import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.schemas import SubscriptionTier


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


def resolve_tier_from_entitlement(
    token: str | None,
    *,
    secret: str,
    default_tier: str,
    required: bool,
) -> SubscriptionTier:
    if not token:
        if required:
            raise HTTPException(status_code=401, detail="Missing entitlement token.")
        return normalize_tier(default_tier)

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
    return normalize_tier(tier)


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
