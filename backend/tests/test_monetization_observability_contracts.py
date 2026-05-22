import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import AgentRunLog, WorkflowQueueJob
from app.services import entitlement_service
from app.services.entitlement_service import sign_entitlement_token
from app.services.orchestration_service import get_monetization_observability


def _default_run_payload() -> dict:
    return {
        "entry_source": "contract-test",
        "steps": [
            {"step_name": "Plan The Day", "agent_type": "planner", "enabled": True},
            {"step_name": "Analyze Technical Signals", "agent_type": "analyzer", "enabled": True},
            {"step_name": "Review And Reflect", "agent_type": "reviewer", "enabled": True},
        ],
        "daily_context": {
            "tasks": ["Investigate flaky release pipeline"],
            "meetings": ["Platform sync"],
            "blockers": ["Need production logs"],
            "priorities": ["Fix pipeline flake"],
        },
        "technical_input": {
            "logs": "upload timed out",
            "errors": ["TimeoutError"],
            "code_snippets": ["curl --max-time 30 https://registry/upload"],
            "issue_description": "artifact upload timeout",
        },
        "reflection_input": {
            "completed": ["Reviewed retry policy"],
            "unfinished": ["Validate queue fallback"],
            "blockers": ["Missing permissions"],
            "mood_or_notes": "steady",
        },
        "persist_knowledge": True,
        "persist_template": False,
    }


def _sign_raw_entitlement_token(*, secret: str, tier: str, exp_epoch: int, user_id: str = "contract-test") -> str:
    payload = {"tier": tier, "user_id": user_id, "exp": exp_epoch}
    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).decode("utf-8").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"


def _tamper_token_signature(token: str) -> str:
    payload_part, signature_part = token.split(".", 1)
    replacement = "0" if signature_part[-1] != "0" else "1"
    return f"{payload_part}.{signature_part[:-1]}{replacement}"


def _single_step_run_payload() -> dict:
    payload = _default_run_payload()
    payload["steps"] = [payload["steps"][0]]
    return payload


def test_entitlement_expired_token_rejected(client) -> None:
    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    try:
        settings.entitlement_secret = "expired-secret"
        settings.entitlement_required = True
        expired_token = _sign_raw_entitlement_token(
            secret="expired-secret",
            tier="pro",
            exp_epoch=int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()),
        )

        response = client.post(
            "/api/orchestrations/run",
            json=_default_run_payload(),
            headers={"X-Entitlement": expired_token},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Entitlement token expired."
    finally:
        settings.entitlement_secret = old_secret
        settings.entitlement_required = old_required


def test_entitlement_signature_mismatch_rejected(client) -> None:
    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    try:
        settings.entitlement_secret = "signature-secret"
        settings.entitlement_required = True
        valid_token = sign_entitlement_token(secret="signature-secret", tier="power", ttl_seconds=600)
        tampered = _tamper_token_signature(valid_token)

        response = client.post(
            "/api/orchestrations/run",
            json=_default_run_payload(),
            headers={"X-Entitlement": tampered},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid entitlement signature."
    finally:
        settings.entitlement_secret = old_secret
        settings.entitlement_required = old_required


def test_entitlement_token_tier_wins_when_legacy_header_mismatches(client) -> None:
    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    old_allow_legacy = settings.allow_legacy_subscription_tier_fallback
    try:
        settings.entitlement_secret = "tier-mismatch-secret"
        settings.entitlement_required = True
        settings.allow_legacy_subscription_tier_fallback = True
        token = sign_entitlement_token(secret="tier-mismatch-secret", tier="power", ttl_seconds=600)

        response = client.post(
            "/api/orchestrations/run",
            json=_default_run_payload(),
            headers={"X-Entitlement": token, "X-Subscription-Tier": "free"},
        )
        assert response.status_code == 200
        assert response.json()["subscription_tier"] == "power"
    finally:
        settings.entitlement_secret = old_secret
        settings.entitlement_required = old_required
        settings.allow_legacy_subscription_tier_fallback = old_allow_legacy


def test_capability_deny_free_tier_surfaces_in_queue_execution(client) -> None:
    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    try:
        settings.entitlement_secret = "queue-free-secret"
        settings.entitlement_required = True
        free_token = sign_entitlement_token(secret="queue-free-secret", tier="free", ttl_seconds=600)

        response = client.post(
            "/api/orchestrations/queue/run",
            json=_default_run_payload(),
            headers={"X-Entitlement": free_token},
        )
        assert response.status_code == 403
        detail = response.json()["detail"]
        assert detail["code"] == "upgrade_required"
        assert detail["capability"] == "multi_step_workflow"
        assert detail["required_tier"] == "pro"
    finally:
        settings.entitlement_secret = old_secret
        settings.entitlement_required = old_required


def test_quota_exceeded_boundary_for_free_tier_returns_429(client, monkeypatch) -> None:
    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    monkeypatch.setitem(entitlement_service.QUOTA_MATRIX, "free", {"window_days": 7, "max_runs": 1})
    try:
        settings.entitlement_secret = "quota-secret"
        settings.entitlement_required = True
        free_token = sign_entitlement_token(secret="quota-secret", tier="free", ttl_seconds=600)

        first = client.post(
            "/api/orchestrations/run",
            json=_single_step_run_payload(),
            headers={"X-Entitlement": free_token},
        )
        second = client.post(
            "/api/orchestrations/run",
            json=_single_step_run_payload(),
            headers={"X-Entitlement": free_token},
        )

        assert first.status_code == 200
        assert second.status_code == 429
        detail = second.json()["detail"]
        assert detail["code"] == "quota_exceeded"
        assert detail["tier"] == "free"
        assert detail["quota"]["limit"] == 1
        assert detail["quota"]["used"] == 1
    finally:
        settings.entitlement_secret = old_secret
        settings.entitlement_required = old_required


def test_observability_metrics_shape_and_history_order_are_stable(client) -> None:
    run_a = client.post("/api/orchestrations/run", json=_default_run_payload())
    run_b = client.post("/api/orchestrations/run", json=_default_run_payload())
    run_c = client.post("/api/orchestrations/run", json=_default_run_payload())
    assert run_a.status_code == 200
    assert run_b.status_code == 200
    assert run_c.status_code == 200

    metrics_response = client.get("/api/orchestrations/metrics?days=7")
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()
    assert list(metrics.keys()) == [
        "period_days",
        "total_runs",
        "weekly_active_orchestrations",
        "partial_success_rate",
        "average_duration_ms",
        "billable_work_units",
        "successful_audited_workflows",
        "approval_required_blocks",
        "template_policy_upgrade_blocks",
        "approved_runs",
        "checkpointed_runs",
        "failed_jobs_needing_owner",
    ]
    assert isinstance(metrics["period_days"], int)
    assert isinstance(metrics["total_runs"], int)
    assert isinstance(metrics["weekly_active_orchestrations"], int)
    assert isinstance(metrics["partial_success_rate"], float)
    assert isinstance(metrics["average_duration_ms"], int)
    assert isinstance(metrics["billable_work_units"], int)
    assert isinstance(metrics["successful_audited_workflows"], int)
    assert isinstance(metrics["approval_required_blocks"], int)
    assert isinstance(metrics["template_policy_upgrade_blocks"], int)
    assert isinstance(metrics["approved_runs"], int)
    assert isinstance(metrics["checkpointed_runs"], int)
    assert isinstance(metrics["failed_jobs_needing_owner"], int)

    history = client.get("/api/orchestrations/history?limit=3")
    assert history.status_code == 200
    ids = [item["id"] for item in history.json()["items"]]
    assert ids == sorted(ids, reverse=True)


def test_observability_aggregation_shape_and_failure_reason_ordering(client) -> None:
    _ = client
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        db.add_all(
            [
                AgentRunLog(
                    task_type="monetization.usage_recorded",
                    input_summary=json.dumps({"subject_id": "sub-A", "endpoint": "/api/orchestrations/run"}),
                    output_summary="ok",
                    status="success",
                    created_at=now,
                ),
                AgentRunLog(
                    task_type="monetization.usage_recorded",
                    input_summary=json.dumps({"subject_id": "sub-B", "endpoint": "/api/orchestrations/run"}),
                    output_summary="ok",
                    status="success",
                    created_at=now,
                ),
                AgentRunLog(
                    task_type="monetization.quota_checked",
                    input_summary="{}",
                    output_summary="ok",
                    status="allowed",
                    created_at=now,
                ),
                AgentRunLog(
                    task_type="monetization.quota_exceeded",
                    input_summary="{}",
                    output_summary="blocked",
                    status="blocked",
                    created_at=now,
                ),
                AgentRunLog(
                    task_type="monetization.capability_blocked_upgrade_required",
                    input_summary="{}",
                    output_summary="blocked",
                    status="blocked",
                    created_at=now,
                ),
            ]
        )
        db.add_all(
            [
                WorkflowQueueJob(
                    status="failed",
                    attempts=1,
                    max_attempts=3,
                    cancel_requested=False,
                    request_json="{}",
                    error_message="alpha-failure",
                    created_at=now,
                    updated_at=now,
                ),
                WorkflowQueueJob(
                    status="failed",
                    attempts=1,
                    max_attempts=3,
                    cancel_requested=False,
                    request_json="{}",
                    error_message="zeta-failure",
                    created_at=now,
                    updated_at=now,
                ),
                WorkflowQueueJob(
                    status="failed",
                    attempts=1,
                    max_attempts=3,
                    cancel_requested=False,
                    request_json="{}",
                    error_message="alpha-failure",
                    created_at=now,
                    updated_at=now,
                ),
                WorkflowQueueJob(
                    status="canceled",
                    attempts=1,
                    max_attempts=3,
                    cancel_requested=True,
                    request_json="{}",
                    error_message="zeta-failure",
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        db.commit()

        snapshot = get_monetization_observability(db, days=7)
        assert list(snapshot.keys()) == [
            "period_days",
            "active_subjects",
            "runs_by_tier",
            "quota_hit_rate",
            "upgrade_intent_count",
            "queue_success_rate",
            "p95_queue_latency_ms",
            "top_failure_reasons",
        ]
        assert snapshot["active_subjects"] == 2
        assert snapshot["quota_hit_rate"] == 0.5
        assert snapshot["upgrade_intent_count"] == 1
        assert snapshot["top_failure_reasons"] == [
            {"reason": "alpha-failure", "count": 2},
            {"reason": "zeta-failure", "count": 2},
        ]
    finally:
        try:
            next(db_generator)
        except StopIteration:
            pass
