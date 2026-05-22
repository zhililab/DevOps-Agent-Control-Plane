import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.schemas import SubscriptionTier


CAPABILITY_MATRIX: dict[SubscriptionTier, dict[str, int | bool | str]] = {
    "free": {
        "max_enabled_steps": 1,
        "queue_enabled": True,
        "required_tier_for_multi_step": "pro",
    },
    "pro": {
        "max_enabled_steps": 3,
        "queue_enabled": True,
        "required_tier_for_multi_step": "pro",
    },
    "power": {
        "max_enabled_steps": 3,
        "queue_enabled": True,
        "required_tier_for_multi_step": "pro",
    },
}

QUOTA_MATRIX: dict[SubscriptionTier, dict[str, int]] = {
    "free": {"window_days": 7, "max_runs": 25},
    "pro": {"window_days": 7, "max_runs": 300},
    "power": {"window_days": 7, "max_runs": 2000},
}


@dataclass(frozen=True)
class EntitlementContext:
    tier: SubscriptionTier
    subject_id: str
    source: str
    billing_subject: str | None = None


def normalize_tier(value: str) -> SubscriptionTier:
    normalized = value.strip().lower()
    if normalized not in {"free", "pro", "power"}:
        return "pro"
    return normalized  # type: ignore[return-value]


def sign_entitlement_token(
    *,
    secret: str,
    tier: str,
    user_id: str = "local-dev",
    ttl_seconds: int = 3600,
) -> str:
    if not secret.strip():
        raise ValueError("Entitlement secret is required to sign token.")
    payload = {
        "tier": normalize_tier(tier),
        "user_id": user_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(seconds=max(60, ttl_seconds))).timestamp()),
    }
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"


def subject_id_for_entitlement_user(user_id: str) -> str:
    raw_subject = user_id.strip() or "anonymous"
    return f"ent:{_subject_hash(raw_subject)}"


def resolve_tier_from_entitlement(
    token: str | None,
    *,
    secret: str,
    default_tier: str,
    required: bool,
) -> SubscriptionTier:
    return resolve_entitlement_context(
        token,
        secret=secret,
        default_tier=default_tier,
        required=required,
    ).tier


def resolve_entitlement_context(
    token: str | None,
    *,
    secret: str,
    default_tier: str,
    required: bool,
) -> EntitlementContext:
    if not token:
        if required:
            raise HTTPException(status_code=401, detail="Missing entitlement token.")
        return EntitlementContext(
            tier=normalize_tier(default_tier),
            subject_id=f"default:{_subject_hash('anonymous')}",
            source="default",
        )

    if not secret.strip():
        raise HTTPException(status_code=500, detail="Entitlement secret is not configured.")

    payload_part, signature_part = _split_token(token)
    expected_signature = hmac.new(secret.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, signature_part):
        raise HTTPException(status_code=401, detail="Invalid entitlement signature.")

    payload = _decode_payload(payload_part)
    exp = int(payload.get("exp", 0))
    if exp <= int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=401, detail="Entitlement token expired.")

    tier = payload.get("tier")
    if not isinstance(tier, str) or not tier.strip():
        raise HTTPException(status_code=401, detail="Entitlement tier is missing.")
    raw_subject = payload.get("user_id")
    if not isinstance(raw_subject, str) or not raw_subject.strip():
        raw_subject = "anonymous"
    billing_subject = raw_subject.strip()
    return EntitlementContext(
        tier=normalize_tier(tier),
        subject_id=subject_id_for_entitlement_user(billing_subject),
        source="entitlement",
        billing_subject=billing_subject,
    )


def resolve_legacy_entitlement_context(legacy_tier: str) -> EntitlementContext:
    tier = normalize_tier(legacy_tier)
    return EntitlementContext(
        tier=tier,
        subject_id=f"legacy:{_subject_hash(f'legacy-{tier}')}",
        source="legacy_header",
    )


def capability_policy_for_tier(tier: str) -> dict[str, int | bool | str]:
    return CAPABILITY_MATRIX[normalize_tier(tier)].copy()


def quota_policy_for_tier(tier: str) -> dict[str, int]:
    return QUOTA_MATRIX[normalize_tier(tier)].copy()


def _split_token(token: str) -> tuple[str, str]:
    parts = token.strip().split(".", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise HTTPException(status_code=401, detail="Malformed entitlement token.")
    return parts[0], parts[1]


def _decode_payload(payload_part: str) -> dict:
    padded = payload_part + "=" * (-len(payload_part) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Malformed entitlement payload.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=401, detail="Malformed entitlement payload.")
    return payload


def _subject_hash(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()[:16]
