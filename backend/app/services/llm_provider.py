from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from time import perf_counter
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import LlmInvocation
from app.schemas import LlmInvocationRead, ReleaseGateDecision, ReleaseGatePrCiInput
from app.services.security_utils import sanitize_for_log


SYSTEM_PROMPT = """You are a conservative PR/CI release-gate reviewer.
Return one JSON object only with these keys:
- decision: approve | block | needs human review
- confidence: number from 0 to 1
- rationale: concise evidence-based explanation
- risks: array of concise risk strings

Decision policy:
- block when evidence indicates credential exposure, destructive data loss, failed rollback, or critical security risk
- needs human review for production changes, migrations, failed/flaky CI, timeouts, unclear ownership, or incomplete evidence
- approve only for low-risk changes with passing CI and sufficient evidence
Do not invent missing evidence and never include credentials in the response."""


@dataclass(frozen=True)
class ProviderDecision:
    decision: ReleaseGateDecision
    confidence: float
    rationale: str
    risks: list[str]
    invocation_id: int
    status: str


def provider_status(settings: Settings | None = None) -> dict[str, object]:
    current = settings or get_settings()
    parsed = urlparse(current.llm_base_url)
    return {
        "enabled": current.llm_enabled,
        "configured": bool(current.llm_enabled and current.llm_api_key.strip() and current.llm_model.strip()),
        "provider": current.llm_provider.strip() or "volcengine_ark_coding_plan",
        "model": current.llm_model.strip(),
        "prompt_version": current.llm_prompt_version.strip() or "pr-ci-gate.v1",
        "base_url_host": parsed.netloc,
        "write_protected": current.effective_evaluation_write_protected,
        "deterministic_gate_remains_authoritative": True,
    }


def invoke_release_gate_model(
    db: Session,
    release_input: ReleaseGatePrCiInput,
    *,
    orchestration_id: int | None = None,
    evaluation_run_id: int | None = None,
    evaluation_case_id: str = "",
    settings: Settings | None = None,
) -> ProviderDecision:
    current = settings or get_settings()
    context = release_input.model_dump(mode="json")
    request_payload = {
        "model": current.llm_model.strip(),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context, sort_keys=True, separators=(",", ":"))},
        ],
        "temperature": 0,
    }
    request_sha256 = hashlib.sha256(
        json.dumps(
            {
                "provider": current.llm_provider,
                "model": current.llm_model,
                "prompt_version": current.llm_prompt_version,
                "payload": request_payload,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    started = perf_counter()
    try:
        _validate_configuration(current)
        with httpx.Client(timeout=max(1.0, current.llm_timeout_seconds), trust_env=False) as client:
            response = client.post(
                f"{current.llm_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {current.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=request_payload,
            )
            response.raise_for_status()
            response_data = response.json()

        parsed = _parse_provider_response(response_data)
        usage = response_data.get("usage") if isinstance(response_data, dict) else {}
        input_tokens = _safe_int(usage.get("prompt_tokens") if isinstance(usage, dict) else 0)
        output_tokens = _safe_int(usage.get("completion_tokens") if isinstance(usage, dict) else 0)
        latency_ms = max(0, round((perf_counter() - started) * 1000))
        record = LlmInvocation(
            orchestration_id=orchestration_id,
            evaluation_run_id=evaluation_run_id,
            evaluation_case_id=evaluation_case_id,
            provider=current.llm_provider.strip() or "volcengine_ark_coding_plan",
            model=str(response_data.get("model") or current.llm_model),
            prompt_version=current.llm_prompt_version.strip() or "pr-ci-gate.v1",
            request_sha256=request_sha256,
            status="success",
            decision=parsed["decision"],
            confidence=parsed["confidence"],
            rationale=parsed["rationale"],
            risks_json=json.dumps(parsed["risks"]),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            estimated_cost_microusd=_estimated_cost_microusd(current, input_tokens, output_tokens),
            error_message="",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return ProviderDecision(
            decision=parsed["decision"],
            confidence=parsed["confidence"],
            rationale=parsed["rationale"],
            risks=parsed["risks"],
            invocation_id=record.id,
            status="success",
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = max(0, round((perf_counter() - started) * 1000))
        error_message = sanitize_for_log(str(exc), max_chars=500) or "Provider request failed."
        record = LlmInvocation(
            orchestration_id=orchestration_id,
            evaluation_run_id=evaluation_run_id,
            evaluation_case_id=evaluation_case_id,
            provider=current.llm_provider.strip() or "volcengine_ark_coding_plan",
            model=current.llm_model.strip() or "unconfigured",
            prompt_version=current.llm_prompt_version.strip() or "pr-ci-gate.v1",
            request_sha256=request_sha256,
            status="failed",
            decision="needs human review",
            confidence=0.0,
            rationale="Provider unavailable; deterministic release gate remained authoritative.",
            risks_json=json.dumps(["Model observation was unavailable."]),
            input_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms,
            estimated_cost_microusd=0,
            error_message=error_message,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return ProviderDecision(
            decision="needs human review",
            confidence=0.0,
            rationale=record.rationale,
            risks=["Model observation was unavailable."],
            invocation_id=record.id,
            status="failed",
        )


def to_invocation_read(record: LlmInvocation) -> LlmInvocationRead:
    try:
        risks = json.loads(record.risks_json or "[]")
    except json.JSONDecodeError:
        risks = ["Stored risk payload could not be decoded."]
    return LlmInvocationRead(
        id=record.id,
        orchestration_id=record.orchestration_id,
        evaluation_run_id=record.evaluation_run_id,
        evaluation_case_id=record.evaluation_case_id,
        provider=record.provider,
        model=record.model,
        prompt_version=record.prompt_version,
        request_sha256=record.request_sha256,
        status=record.status,
        decision=record.decision,
        confidence=record.confidence,
        rationale=record.rationale,
        risks=[str(item) for item in risks if isinstance(item, str)],
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        latency_ms=record.latency_ms,
        estimated_cost_usd=record.estimated_cost_microusd / 1_000_000,
        error_message=record.error_message,
        created_at=record.created_at,
    )


def _validate_configuration(settings: Settings) -> None:
    if not settings.llm_enabled:
        raise RuntimeError("LLM provider is disabled.")
    if not settings.llm_api_key.strip():
        raise RuntimeError("LLM provider API key is not configured.")
    if not settings.llm_model.strip():
        raise RuntimeError("LLM provider model is not configured.")


def _parse_provider_response(data: object) -> dict[str, object]:
    if not isinstance(data, dict):
        raise ValueError("Provider returned a non-object response.")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Provider response did not contain choices.")
    first = choices[0]
    if not isinstance(first, dict) or not isinstance(first.get("message"), dict):
        raise ValueError("Provider response did not contain a message.")
    content = first["message"].get("content")
    if not isinstance(content, str):
        raise ValueError("Provider response content was not text.")
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Provider response did not contain a JSON object.")
    parsed = json.loads(content[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Provider decision payload was not an object.")
    decision = _normalize_decision(parsed.get("decision"))
    confidence = min(1.0, max(0.0, _safe_float(parsed.get("confidence"))))
    rationale = sanitize_for_log(str(parsed.get("rationale") or "No rationale supplied."), max_chars=2000)
    raw_risks = parsed.get("risks")
    risks = [sanitize_for_log(str(item), max_chars=500) for item in raw_risks] if isinstance(raw_risks, list) else []
    return {
        "decision": decision,
        "confidence": confidence,
        "rationale": rationale,
        "risks": [risk for risk in risks if risk],
    }


def _normalize_decision(value: object) -> ReleaseGateDecision:
    normalized = str(value or "").strip().lower().replace("_", " ")
    if normalized in {"approve", "approved", "pass"}:
        return "approve"
    if normalized in {"block", "blocked", "reject"}:
        return "block"
    return "needs human review"


def _safe_int(value: object) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _estimated_cost_microusd(settings: Settings, input_tokens: int, output_tokens: int) -> int:
    return max(
        0,
        round(
            input_tokens * settings.llm_input_cost_per_million_usd
            + output_tokens * settings.llm_output_cost_per_million_usd
        ),
    )
