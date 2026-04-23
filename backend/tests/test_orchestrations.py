from app.config import get_settings
from app.services.entitlement_service import sign_entitlement_token


def _default_run_payload() -> dict:
    return {
        "entry_source": "test-suite",
        "steps": [
            {"step_name": "Plan The Day", "agent_type": "planner", "enabled": True},
            {"step_name": "Analyze Technical Signals", "agent_type": "analyzer", "enabled": True},
            {"step_name": "Review And Reflect", "agent_type": "reviewer", "enabled": True},
        ],
        "daily_context": {
            "tasks": ["Fix flaky pipeline"],
            "meetings": ["Platform sync"],
            "blockers": ["Need owner approval"],
            "priorities": ["Fix flaky pipeline"],
        },
        "technical_input": {
            "logs": "upload timed out",
            "errors": ["TimeoutError"],
            "code_snippets": ["curl --max-time 30 https://registry/upload"],
            "issue_description": "artifact upload timeout",
        },
        "reflection_input": {
            "completed": ["Reviewed logs"],
            "unfinished": ["Validate retry strategy"],
            "blockers": ["Missing owner"],
            "mood_or_notes": "steady",
        },
        "persist_knowledge": True,
        "persist_template": False,
    }


def test_orchestration_run_success_and_history_and_get(client) -> None:
    create_response = client.post("/api/orchestrations/run", json=_default_run_payload())
    assert create_response.status_code == 200
    created = create_response.json()

    assert created["status"] == "success"
    assert created["subscription_tier"] == "pro"
    assert len(created["steps"]) == 3
    for step in created["steps"]:
        assert step["audit"]["conclusion"]
        assert step["audit"]["evidence"]
        assert step["audit"]["risk"]
        assert step["audit"]["next_action"]

    history_response = client.get("/api/orchestrations/history")
    assert history_response.status_code == 200
    history = history_response.json()["items"]
    assert len(history) == 1
    assert history[0]["id"] == created["id"]

    detail_response = client.get(f"/api/orchestrations/{created['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == created["id"]
    assert len(detail["steps"]) == 3


def test_orchestration_partial_success_when_analyzer_missing_signal(client) -> None:
    payload = _default_run_payload()
    payload["technical_input"] = None
    response = client.post("/api/orchestrations/run", json=payload)
    assert response.status_code == 200
    record = response.json()

    assert record["status"] == "partial_success"
    analyzer = next(step for step in record["steps"] if step["agent_type"] == "analyzer")
    assert analyzer["status"] == "failed"
    assert analyzer["fallback_action"]


def test_orchestration_free_tier_blocks_cross_workflow(client) -> None:
    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    settings.entitlement_secret = "free-tier-secret"
    settings.entitlement_required = True
    free_token = sign_entitlement_token(secret="free-tier-secret", tier="free", ttl_seconds=600)
    response = client.post(
        "/api/orchestrations/run",
        json=_default_run_payload(),
        headers={"X-Entitlement": free_token},
    )
    try:
        assert response.status_code == 403
        assert "single-step workflow" in response.json()["detail"]
    finally:
        settings.entitlement_secret = old_secret
        settings.entitlement_required = old_required


def test_workflow_template_import_export_round_trip(client) -> None:
    create_template = client.post(
        "/api/orchestrations/templates",
        json={
            "name": "Daily DevOps Loop",
            "description": "Plan + Analyze + Review",
            "steps": [
                {"step_name": "Plan The Day", "agent_type": "planner", "enabled": True},
                {"step_name": "Analyze Technical Signals", "agent_type": "analyzer", "enabled": True},
                {"step_name": "Review And Reflect", "agent_type": "reviewer", "enabled": True},
            ],
            "tags": ["devops", "daily"],
            "enabled": True,
        },
    )
    assert create_template.status_code == 200
    template_id = create_template.json()["id"]

    export_response = client.get("/api/orchestrations/templates/export")
    assert export_response.status_code == 200
    exported = export_response.json()
    assert len(exported) >= 1

    import_response = client.post(
        "/api/orchestrations/templates/import",
        json={"items": exported, "upsert_by_name": True},
    )
    assert import_response.status_code == 200
    result = import_response.json()
    assert result["total"] >= 1
    assert result["imported"] + result["updated"] >= 1

    run_from_template = client.post(
        "/api/orchestrations/run",
        json={
            "entry_source": "template-run",
            "template_id": template_id,
            "daily_context": {
                "tasks": ["Fix CI"],
                "meetings": ["Sync"],
                "blockers": ["None"],
                "priorities": ["Fix CI"],
            },
            "technical_input": {
                "logs": "timeout",
                "errors": ["TimeoutError"],
                "code_snippets": ["curl --max-time 30 https://example.com"],
                "issue_description": "upload timeout",
            },
            "reflection_input": {
                "completed": ["triage"],
                "unfinished": ["validate"],
                "blockers": [],
                "mood_or_notes": "ok",
            },
        },
    )
    assert run_from_template.status_code == 200
    assert run_from_template.json()["status"] == "success"


def test_orchestration_metrics_reports_weekly_activity(client) -> None:
    run_response = client.post("/api/orchestrations/run", json=_default_run_payload())
    assert run_response.status_code == 200

    metrics_response = client.get("/api/orchestrations/metrics?days=7")
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()

    assert metrics["period_days"] == 7
    assert metrics["total_runs"] >= 1
    assert metrics["weekly_active_orchestrations"] >= 1
    assert "partial_success_rate" in metrics
    assert "average_duration_ms" in metrics


def test_signed_entitlement_enforced_when_required(client) -> None:
    settings = get_settings()
    old_required = settings.entitlement_required
    old_secret = settings.entitlement_secret
    try:
        settings.entitlement_required = True
        settings.entitlement_secret = "test-secret"
        no_token = client.post("/api/orchestrations/run", json=_default_run_payload())
        assert no_token.status_code == 401

        token = sign_entitlement_token(secret="test-secret", tier="power", ttl_seconds=600)
        ok_response = client.post(
            "/api/orchestrations/run",
            json=_default_run_payload(),
            headers={"X-Entitlement": token},
        )
        assert ok_response.status_code == 200
        assert ok_response.json()["subscription_tier"] == "power"
    finally:
        settings.entitlement_required = old_required
        settings.entitlement_secret = old_secret


def test_queue_run_status_retry_and_cancel(client) -> None:
    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    try:
        settings.entitlement_secret = "queue-secret"
        settings.entitlement_required = True
        token = sign_entitlement_token(secret="queue-secret", tier="pro", ttl_seconds=600)

        run_response = client.post(
            "/api/orchestrations/queue/run",
            json=_default_run_payload(),
            headers={"X-Entitlement": token},
        )
        assert run_response.status_code == 200
        job = run_response.json()
        assert job["status"] in {"queued", "running", "succeeded"}
        job_id = job["job_id"]

        status_response = client.get(f"/api/orchestrations/queue/{job_id}")
        assert status_response.status_code == 200
        current = status_response.json()
        assert current["status"] in {"running", "succeeded", "queued"}

        cancel_response = client.post(f"/api/orchestrations/queue/{job_id}/cancel")
        # Cancel may race with completion; if completed, API returns 409 by design.
        assert cancel_response.status_code in {200, 409}

        if cancel_response.status_code == 200:
            retry_response = client.post(f"/api/orchestrations/queue/{job_id}/retry")
            assert retry_response.status_code == 200
            assert retry_response.json()["job_id"] == job_id
    finally:
        settings.entitlement_secret = old_secret
        settings.entitlement_required = old_required
