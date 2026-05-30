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
    payload = {
        **_default_run_payload(),
        "team_subject": "platform-team",
        "requested_by": "alice@sre",
        "approval_actor": "bob@platform",
        "approval_note": "Approved release readiness demo.",
    }
    create_response = client.post("/api/orchestrations/run", json=payload)
    assert create_response.status_code == 200
    created = create_response.json()

    assert created["status"] == "success"
    assert created["subscription_tier"] == "pro"
    assert created["team_subject"] == "platform-team"
    assert created["requested_by"] == "alice@sre"
    assert created["approval_actor"] == "bob@platform"
    assert created["policy_gate"]["template_name"] == "Custom workflow"
    assert created["policy_gate"]["decision"] == "needs human review"
    assert created["billable_work_units"] == 3
    assert created["checkpoint_count"] >= 8
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
    assert history[0]["checkpoint_count"] >= 8
    assert history[0]["ledger_integrity"] == {
        "entity_type": "orchestration",
        "entity_id": str(created["id"]),
        "integrity_status": "valid",
        "event_count": 5,
    }

    detail_response = client.get(f"/api/orchestrations/{created['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == created["id"]
    assert len(detail["steps"]) == 3
    assert detail["policy_gate"]["billable_work_units"] == 3

    checkpoint_response = client.get(f"/api/orchestrations/{created['id']}/checkpoints")
    assert checkpoint_response.status_code == 200
    checkpoints = checkpoint_response.json()["items"]
    checkpoint_types = [item["checkpoint_type"] for item in checkpoints]
    assert "orchestration.accepted" in checkpoint_types
    assert "orchestration.success" in checkpoint_types
    assert checkpoint_types.count("step.started") == 3
    assert all(item["integrity_status"] == "valid" for item in checkpoints)

    filtered_history = client.get("/api/orchestrations/history?team_subject=platform-team")
    assert filtered_history.status_code == 200
    assert [item["id"] for item in filtered_history.json()["items"]] == [created["id"]]

    empty_history = client.get("/api/orchestrations/history?team_subject=other-team")
    assert empty_history.status_code == 200
    assert empty_history.json()["items"] == []


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

    checkpoints = client.get(f"/api/orchestrations/{record['id']}/checkpoints").json()["items"]
    failed = [item for item in checkpoints if item["checkpoint_type"] == "step.failed"]
    assert len(failed) == 1
    assert failed[0]["payload"]["fallback_action"] == "Gather one concrete error signal and rerun analyzer."


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


def test_template_policy_requires_human_approval(client) -> None:
    create_template = client.post(
        "/api/orchestrations/templates",
        json={
            "name": "Approval Required Migration",
            "description": "High-risk migration gate",
            "steps": [
                {"step_name": "Plan Migration", "agent_type": "planner", "enabled": True},
                {"step_name": "Review Migration", "agent_type": "reviewer", "enabled": True},
            ],
            "tags": ["migration"],
            "policy": {
                "required_tier": "pro",
                "risk_level": "high",
                "approval_required": True,
                "allowed_tool_scopes": ["database-migration"],
                "billable_work_units": 5,
            },
            "enabled": True,
        },
    )
    assert create_template.status_code == 200
    template_id = create_template.json()["id"]

    payload = {
        **_default_run_payload(),
        "template_id": template_id,
        "steps": None,
    }
    blocked = client.post("/api/orchestrations/run", json=payload)
    assert blocked.status_code == 409
    detail = blocked.json()["detail"]
    assert detail["code"] == "approval_required"
    assert detail["risk_level"] == "high"

    approved = client.post(
        "/api/orchestrations/run",
        json={**payload, "approval_confirmed": True},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "success"


def test_ai_generated_pr_release_gate_returns_policy_decision_and_roi_evidence(client) -> None:
    import_response = client.post("/api/orchestrations/templates/import/builtin")
    assert import_response.status_code == 200
    templates_response = client.get("/api/orchestrations/templates")
    assert templates_response.status_code == 200
    ai_pr_template = next(
        item for item in templates_response.json() if item["name"] == "AI-generated PR Release Gate"
    )

    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    try:
        settings.entitlement_secret = "ai-pr-release-gate-secret"
        settings.entitlement_required = True
        token = sign_entitlement_token(secret="ai-pr-release-gate-secret", tier="power", ttl_seconds=600)

        response = client.post(
            "/api/orchestrations/run",
            json={
                "entry_source": "test-suite",
                "template_id": ai_pr_template["id"],
                "steps": None,
                "team_subject": "platform-team",
                "requested_by": "coding-agent",
                "approval_actor": "release-manager",
                "approval_note": "Human approved the PR release gate after CI review.",
                "approval_confirmed": True,
                "daily_context": {
                    "tasks": ["PR diff: Coding Agent changed CI/CD release workflow."],
                    "meetings": ["Release manager review"],
                    "blockers": ["Human approval required before production rollout"],
                    "priorities": ["staging -> production"],
                },
                "technical_input": {
                    "logs": "tests passed\nrelease gate waiting for approval",
                    "errors": ["CI warning: production release needs approval"],
                    "code_snippets": ["git diff --stat origin/main...HEAD"],
                    "issue_description": "AI-generated PR changes production deployment behavior.",
                },
                "release_gate_input": {
                    "pr_url": "https://github.com/example/platform/pull/1842",
                    "pr_diff_summary": "Generated PR changes CI/CD release workflow. token=should-not-leak",
                    "ci_log_summary": "tests passed; k8s dry-run passed; authorization: Bearer abc123",
                    "target_environment": "staging -> production",
                    "change_risk": "high risk generated deployment path change",
                },
                "reflection_input": {
                    "completed": ["PR diff summarized", "CI logs attached"],
                    "unfinished": ["Release manager approval"],
                    "blockers": ["Production remains blocked without approval"],
                    "mood_or_notes": "Decision must be approve, block, or needs human review.",
                },
            },
            headers={"X-Entitlement": token},
        )
    finally:
        settings.entitlement_secret = old_secret
        settings.entitlement_required = old_required

    assert response.status_code == 200
    record = response.json()
    assert record["status"] == "success"
    assert record["subscription_tier"] == "power"
    assert record["billable_work_units"] == 8
    assert record["policy_gate"] == {
        "template_id": ai_pr_template["id"],
        "template_name": "AI-generated PR Release Gate",
        "required_tier": "power",
        "risk_level": "high",
        "approval_required": True,
        "approval_confirmed": True,
        "allowed_tool_scopes": ["ci-cd-release-gate"],
        "billable_work_units": 8,
        "decision": "needs human review",
    }
    assert "Decision: needs human review" in record["summary"]["conclusion"]
    assert any("Blocked risk" in risk for risk in record["summary"]["risks"])
    assert all(step["audit"]["evidence"] for step in record["steps"])
    assert "should-not-leak" not in record["steps"][0]["audit"]["evidence"]
    assert record["roi_evidence"] == {
        "review_time_saved_minutes": 63,
        "audit_time_saved_minutes": 50,
        "blocked_risk_count": 1,
        "blocked_risk_value_usd": 5000,
        "estimated_customer_value_usd": 5283,
        "billable_work_units": 8,
        "assumptions": [
            "Engineering review time is estimated at 6 minutes per billable work unit plus approval overhead.",
            "Audit time is estimated from work units and checkpoint-ready evidence.",
            "Blocked risk value uses low=$250, medium=$1000, high=$5000, critical=$15000 per blocked risk.",
            "ROI evidence is directional for buyer demos and pilot review, not billing data.",
        ],
    }

    evidence_response = client.get(f"/api/orchestrations/{record['id']}/evidence")
    assert evidence_response.status_code == 200
    evidence = evidence_response.json()
    assert evidence["orchestration_id"] == record["id"]
    assert evidence["format"] == "markdown"
    assert "Orchestration Evidence Export" in evidence["markdown"]
    assert "PR / CI Context" in evidence["markdown"]
    assert "ROI Evidence" in evidence["markdown"]
    serialized = str(evidence)
    assert "should-not-leak" not in serialized
    assert "Bearer abc123" not in serialized
    assert "<redacted>" in serialized


def test_pilot_scenarios_are_stable_redacted_and_runnable(client) -> None:
    scenarios_response = client.get("/api/orchestrations/pilot-scenarios")
    assert scenarios_response.status_code == 200
    scenarios = scenarios_response.json()["items"]
    assert [item["id"] for item in scenarios] == [
        "high-risk-generated-pr",
        "low-risk-docs-pr",
        "ci-flaky-release",
        "missing-approval",
        "rollback-sensitive-release",
    ]
    assert all(item["release_gate_input"] for item in scenarios)
    serialized = str(scenarios).lower()
    for forbidden in ("token", "password", "secret", "raw entitlement"):
        assert forbidden not in serialized

    import_response = client.post("/api/orchestrations/templates/import/builtin")
    assert import_response.status_code == 200
    templates_response = client.get("/api/orchestrations/templates")
    ai_pr_template = next(
        item for item in templates_response.json() if item["name"] == "AI-generated PR Release Gate"
    )
    scenario = next(item for item in scenarios if item["id"] == "high-risk-generated-pr")

    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    try:
        settings.entitlement_secret = "pilot-scenario-secret"
        settings.entitlement_required = True
        power_token = sign_entitlement_token(secret="pilot-scenario-secret", tier="power", ttl_seconds=600)

        response = client.post(
            "/api/orchestrations/run",
            json={
                "entry_source": "pilot_scenario",
                "pilot_scenario_id": scenario["id"],
                "template_id": ai_pr_template["id"],
                "steps": None,
                "team_subject": "platform-team",
                "requested_by": "sre-lead",
                "approval_actor": "release-manager",
                "approval_note": "Pilot scenario approval confirmed.",
                "approval_confirmed": scenario["approval_confirmed"],
                "release_gate_input": scenario["release_gate_input"],
                "daily_context": scenario["daily_context"],
                "technical_input": scenario["technical_input"],
                "reflection_input": scenario["reflection_input"],
                "persist_knowledge": False,
                "persist_template": False,
            },
            headers={"X-Entitlement": power_token},
        )
    finally:
        settings.entitlement_secret = old_secret
        settings.entitlement_required = old_required

    assert response.status_code == 200
    record = response.json()
    assert record["status"] == "success"
    assert record["pilot_scenario_id"] == "high-risk-generated-pr"
    assert record["policy_gate"]["template_name"] == "AI-generated PR Release Gate"
    assert record["policy_gate"]["decision"] == "needs human review"
    assert record["roi_evidence"]["estimated_customer_value_usd"] > 0
    assert record["checkpoint_count"] > 0


def test_missing_approval_pilot_scenario_blocks_until_confirmed(client) -> None:
    client.post("/api/orchestrations/templates/import/builtin")
    ai_pr_template = next(
        item for item in client.get("/api/orchestrations/templates").json()
        if item["name"] == "AI-generated PR Release Gate"
    )
    scenario = next(
        item for item in client.get("/api/orchestrations/pilot-scenarios").json()["items"]
        if item["id"] == "missing-approval"
    )

    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    try:
        settings.entitlement_secret = "missing-approval-secret"
        settings.entitlement_required = True
        power_token = sign_entitlement_token(secret="missing-approval-secret", tier="power", ttl_seconds=600)
        payload = {
            "entry_source": "pilot_scenario",
            "pilot_scenario_id": scenario["id"],
            "template_id": ai_pr_template["id"],
            "steps": None,
            "team_subject": "platform-team",
            "requested_by": "sre-lead",
            "approval_actor": "release-manager",
            "approval_note": "Approval not confirmed for this scenario.",
            "approval_confirmed": False,
            "release_gate_input": scenario["release_gate_input"],
            "daily_context": scenario["daily_context"],
            "technical_input": scenario["technical_input"],
            "reflection_input": scenario["reflection_input"],
            "persist_knowledge": False,
            "persist_template": False,
        }
        blocked = client.post(
            "/api/orchestrations/run",
            json=payload,
            headers={"X-Entitlement": power_token},
        )
        approved = client.post(
            "/api/orchestrations/run",
            json={**payload, "approval_confirmed": True, "approval_note": "Release manager approved the pilot run."},
            headers={"X-Entitlement": power_token},
        )
    finally:
        settings.entitlement_secret = old_secret
        settings.entitlement_required = old_required

    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "approval_required"
    assert approved.status_code == 200
    assert approved.json()["policy_gate"]["approval_confirmed"] is True


def test_template_policy_required_tier_blocks_lower_tier(client) -> None:
    create_template = client.post(
        "/api/orchestrations/templates",
        json={
            "name": "Power Only Smoke",
            "description": "Single-step power-tier policy test",
            "steps": [
                {"step_name": "Plan Power Gate", "agent_type": "planner", "enabled": True},
            ],
            "tags": ["power-only"],
            "policy": {
                "required_tier": "power",
                "risk_level": "medium",
                "approval_required": False,
                "allowed_tool_scopes": ["none"],
                "billable_work_units": 2,
            },
            "enabled": True,
        },
    )
    assert create_template.status_code == 200

    response = client.post(
        "/api/orchestrations/run",
        json={
            **_default_run_payload(),
            "template_id": create_template.json()["id"],
            "steps": None,
        },
    )
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["capability"] == "template_policy"
    assert detail["required_tier"] == "power"


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
    assert metrics["billable_work_units"] >= 1
    assert metrics["successful_audited_workflows"] >= 1
    assert "approval_required_blocks" in metrics
    assert "template_policy_upgrade_blocks" in metrics


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


def test_production_mode_requires_signed_entitlement_and_disables_legacy_tier_header(client) -> None:
    settings = get_settings()
    old_environment = settings.environment
    old_required = settings.entitlement_required
    old_secret = settings.entitlement_secret
    old_allow_legacy = settings.allow_legacy_subscription_tier_fallback
    try:
        settings.environment = "production"
        settings.entitlement_required = False
        settings.allow_legacy_subscription_tier_fallback = True
        settings.entitlement_secret = "prod-secret"

        legacy_only = client.post(
            "/api/orchestrations/run",
            json=_default_run_payload(),
            headers={"X-Subscription-Tier": "power"},
        )
        assert legacy_only.status_code == 401

        token = sign_entitlement_token(secret="prod-secret", tier="power", ttl_seconds=600)
        token_response = client.post(
            "/api/orchestrations/run",
            json=_default_run_payload(),
            headers={"X-Entitlement": token},
        )
        assert token_response.status_code == 200
        assert token_response.json()["subscription_tier"] == "power"
    finally:
        settings.environment = old_environment
        settings.entitlement_required = old_required
        settings.entitlement_secret = old_secret
        settings.allow_legacy_subscription_tier_fallback = old_allow_legacy


def test_non_production_allows_legacy_tier_header_when_explicitly_enabled(client) -> None:
    settings = get_settings()
    old_environment = settings.environment
    old_required = settings.entitlement_required
    old_allow_legacy = settings.allow_legacy_subscription_tier_fallback
    try:
        settings.environment = "local"
        settings.entitlement_required = False
        settings.allow_legacy_subscription_tier_fallback = True

        response = client.post(
            "/api/orchestrations/run",
            json=_default_run_payload(),
            headers={"X-Subscription-Tier": "power"},
        )
        assert response.status_code == 200
        assert response.json()["subscription_tier"] == "power"
    finally:
        settings.environment = old_environment
        settings.entitlement_required = old_required
        settings.allow_legacy_subscription_tier_fallback = old_allow_legacy


def test_non_production_ignores_legacy_tier_header_when_fallback_disabled(client) -> None:
    settings = get_settings()
    old_environment = settings.environment
    old_required = settings.entitlement_required
    old_allow_legacy = settings.allow_legacy_subscription_tier_fallback
    old_default_tier = settings.default_subscription_tier
    try:
        settings.environment = "local"
        settings.entitlement_required = False
        settings.allow_legacy_subscription_tier_fallback = False
        settings.default_subscription_tier = "pro"

        response = client.post(
            "/api/orchestrations/run",
            json=_default_run_payload(),
            headers={"X-Subscription-Tier": "power"},
        )
        assert response.status_code == 200
        assert response.json()["subscription_tier"] == "pro"
    finally:
        settings.environment = old_environment
        settings.entitlement_required = old_required
        settings.allow_legacy_subscription_tier_fallback = old_allow_legacy
        settings.default_subscription_tier = old_default_tier


def test_queue_production_mode_requires_signed_entitlement(client) -> None:
    settings = get_settings()
    old_environment = settings.environment
    old_required = settings.entitlement_required
    old_secret = settings.entitlement_secret
    old_allow_legacy = settings.allow_legacy_subscription_tier_fallback
    try:
        settings.environment = "production"
        settings.entitlement_required = False
        settings.allow_legacy_subscription_tier_fallback = True
        settings.entitlement_secret = "queue-prod-secret"

        legacy_only = client.post(
            "/api/orchestrations/queue/run",
            json=_default_run_payload(),
            headers={"X-Subscription-Tier": "power"},
        )
        assert legacy_only.status_code == 401

        token = sign_entitlement_token(secret="queue-prod-secret", tier="pro", ttl_seconds=600)
        token_response = client.post(
            "/api/orchestrations/queue/run",
            json=_default_run_payload(),
            headers={"X-Entitlement": token},
        )
        assert token_response.status_code == 200
        assert token_response.json()["status"] in {"queued", "running", "succeeded"}
    finally:
        settings.environment = old_environment
        settings.entitlement_required = old_required
        settings.entitlement_secret = old_secret
        settings.allow_legacy_subscription_tier_fallback = old_allow_legacy


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
        assert isinstance(current.get("events"), list)
        assert len(current["events"]) >= 1
        assert any(item["event_type"] == "queued" for item in current["events"])
        assert isinstance(current.get("checkpoints"), list)
        assert any(item["checkpoint_type"] == "queue.queued" for item in current["checkpoints"])
        assert current["team_subject"] == "demo-team"

        cancel_response = client.post(f"/api/orchestrations/queue/{job_id}/cancel?actor=queue-owner")
        # Cancel may race with completion; if completed, API returns 409 by design.
        assert cancel_response.status_code in {200, 409}

        if cancel_response.status_code == 200:
            canceled_job = cancel_response.json()
            assert any(item["checkpoint_type"] == "queue.cancel_requested" for item in canceled_job["checkpoints"])
            retry_response = client.post(f"/api/orchestrations/queue/{job_id}/retry?actor=queue-owner")
            assert retry_response.status_code == 200
            assert retry_response.json()["job_id"] == job_id
    finally:
        settings.entitlement_secret = old_secret
        settings.entitlement_required = old_required


def test_queue_history_endpoint_lists_jobs(client) -> None:
    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    try:
        settings.entitlement_secret = "queue-history-secret"
        settings.entitlement_required = True
        token = sign_entitlement_token(secret="queue-history-secret", tier="pro", ttl_seconds=600)

        run_response = client.post(
            "/api/orchestrations/queue/run",
            json=_default_run_payload(),
            headers={"X-Entitlement": token},
        )
        assert run_response.status_code == 200

        history_response = client.get("/api/orchestrations/queue/history?limit=20")
        assert history_response.status_code == 200
        history_items = history_response.json()["items"]
        assert len(history_items) >= 1
        assert "status" in history_items[0]
        assert "attempts" in history_items[0]
        assert history_items[0]["events"] == []
        assert history_items[0]["checkpoints"] == []

        filtered_response = client.get("/api/orchestrations/queue/history?team_subject=demo-team&limit=20")
        assert filtered_response.status_code == 200
        assert len(filtered_response.json()["items"]) >= 1
    finally:
        settings.entitlement_secret = old_secret
        settings.entitlement_required = old_required


def test_entitlement_bootstrap_endpoint_disabled_by_default(client) -> None:
    settings = get_settings()
    old_enabled = settings.enable_public_entitlement_bootstrap
    old_secret = settings.entitlement_secret
    try:
        settings.enable_public_entitlement_bootstrap = False
        settings.entitlement_secret = "bootstrap-secret"
        response = client.get("/api/orchestrations/entitlement/bootstrap")
        assert response.status_code == 404
    finally:
        settings.enable_public_entitlement_bootstrap = old_enabled
        settings.entitlement_secret = old_secret


def test_entitlement_bootstrap_endpoint_returns_signed_token_when_enabled(client) -> None:
    settings = get_settings()
    old_enabled = settings.enable_public_entitlement_bootstrap
    old_secret = settings.entitlement_secret
    old_ttl = settings.public_entitlement_bootstrap_ttl_seconds
    old_default_tier = settings.default_subscription_tier
    try:
        settings.enable_public_entitlement_bootstrap = True
        settings.entitlement_secret = "bootstrap-secret"
        settings.public_entitlement_bootstrap_ttl_seconds = 600
        settings.default_subscription_tier = "pro"

        response = client.get("/api/orchestrations/entitlement/bootstrap")
        assert response.status_code == 200
        body = response.json()
        assert body["tier"] == "pro"
        assert isinstance(body["token"], str) and "." in body["token"]
        assert "expires_at" in body
    finally:
        settings.enable_public_entitlement_bootstrap = old_enabled
        settings.entitlement_secret = old_secret
        settings.public_entitlement_bootstrap_ttl_seconds = old_ttl
        settings.default_subscription_tier = old_default_tier
