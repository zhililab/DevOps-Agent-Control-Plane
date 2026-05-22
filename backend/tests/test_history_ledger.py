from app.database import SessionLocal
from app.config import get_settings
from app.models import HistoryEvent, WorkflowCheckpoint
from app.services.entitlement_service import sign_entitlement_token
from app.services.history_ledger import backfill_history_events


def _default_run_payload() -> dict:
    return {
        "entry_source": "ledger-test",
        "steps": [
            {"step_name": "Plan The Day", "agent_type": "planner", "enabled": True},
            {"step_name": "Analyze Technical Signals", "agent_type": "analyzer", "enabled": True},
            {"step_name": "Review And Reflect", "agent_type": "reviewer", "enabled": True},
        ],
        "daily_context": {
            "tasks": ["Verify history ledger"],
            "meetings": [],
            "blockers": [],
            "priorities": ["Verify history ledger"],
        },
        "technical_input": {
            "logs": "deploy finished",
            "errors": [],
            "code_snippets": ["curl http://service/health"],
            "issue_description": "verify deployment history",
        },
        "reflection_input": {
            "completed": ["Added ledger"],
            "unfinished": ["Verify API"],
            "blockers": [],
            "mood_or_notes": "focused",
        },
        "persist_knowledge": False,
        "persist_template": False,
    }


def test_orchestration_run_writes_valid_history_events_without_raw_entitlement_token(client) -> None:
    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    settings.entitlement_secret = "ledger-secret"
    settings.entitlement_required = True
    token = sign_entitlement_token(secret="ledger-secret", tier="pro", user_id="ledger-user", ttl_seconds=600)
    payload = _default_run_payload()
    payload["technical_input"]["logs"] = f"Authorization: Bearer {token}\npassword=super-secret"
    response = client.post("/api/orchestrations/run", json=payload, headers={"X-Entitlement": token})
    settings.entitlement_secret = old_secret
    settings.entitlement_required = old_required
    assert response.status_code == 200
    run_id = response.json()["id"]

    history_response = client.get(f"/api/orchestrations/{run_id}/history-events")
    assert history_response.status_code == 200
    history = history_response.json()

    assert history["integrity_status"] == "valid"
    assert history["event_count"] >= 5
    event_types = [event["event_type"] for event in history["events"]]
    assert "orchestration.accepted" in event_types
    assert "orchestration.success" in event_types
    assert event_types.count("step.success") == 3

    with SessionLocal() as db:
        payloads = "\n".join(event.payload_json for event in db.query(HistoryEvent).all())
    assert token not in payloads
    assert "ledger-secret" not in payloads
    assert "super-secret" not in payloads

    checkpoint_response = client.get(f"/api/orchestrations/{run_id}/checkpoints")
    assert checkpoint_response.status_code == 200
    checkpoint_payloads = "\n".join(str(item["payload"]) for item in checkpoint_response.json()["items"])
    assert token not in checkpoint_payloads
    assert "ledger-secret" not in checkpoint_payloads
    assert "super-secret" not in checkpoint_payloads


def test_partial_success_history_event_preserves_failed_step_and_fallback(client) -> None:
    payload = _default_run_payload()
    payload["technical_input"] = None
    response = client.post("/api/orchestrations/run", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial_success"

    history_response = client.get(f"/api/orchestrations/{body['id']}/history-events")
    assert history_response.status_code == 200
    failed_steps = [
        event for event in history_response.json()["events"]
        if event["event_type"] == "step.failed"
    ]
    assert len(failed_steps) == 1
    assert failed_steps[0]["payload"]["fallback_action"] == "Gather one concrete error signal and rerun analyzer."
    assert failed_steps[0]["payload"]["audit"]["risk"]


def test_history_backfill_is_idempotent(client) -> None:
    response = client.post("/api/orchestrations/run", json=_default_run_payload())
    assert response.status_code == 200

    with SessionLocal() as db:
        first_created = backfill_history_events(db)
        after_first = db.query(HistoryEvent).count()
        second_created = backfill_history_events(db)
        after_second = db.query(HistoryEvent).count()

    assert first_created > 0
    assert second_created == 0
    assert after_second == after_first


def test_history_integrity_detects_payload_tampering(client) -> None:
    response = client.post("/api/orchestrations/run", json=_default_run_payload())
    assert response.status_code == 200
    run_id = response.json()["id"]

    with SessionLocal() as db:
        event = (
            db.query(HistoryEvent)
            .filter(HistoryEvent.entity_type == "orchestration", HistoryEvent.entity_id == str(run_id))
            .order_by(HistoryEvent.id.asc())
            .first()
        )
        assert event is not None
        event.payload_json = '{"tampered":true}'
        db.add(event)
        db.commit()

    history_response = client.get(f"/api/orchestrations/{run_id}/history-events")
    assert history_response.status_code == 200
    history = history_response.json()
    assert history["integrity_status"] == "invalid"
    assert any(event["integrity_error"] == "payload_sha256 mismatch" for event in history["events"])


def test_checkpoint_integrity_detects_payload_tampering(client) -> None:
    response = client.post("/api/orchestrations/run", json=_default_run_payload())
    assert response.status_code == 200
    run_id = response.json()["id"]

    with SessionLocal() as db:
        checkpoint = (
            db.query(WorkflowCheckpoint)
            .filter(WorkflowCheckpoint.orchestration_id == run_id)
            .order_by(WorkflowCheckpoint.id.asc())
            .first()
        )
        assert checkpoint is not None
        checkpoint.payload_json = '{"tampered":true}'
        db.add(checkpoint)
        db.commit()

    checkpoint_response = client.get(f"/api/orchestrations/{run_id}/checkpoints")
    assert checkpoint_response.status_code == 200
    checkpoints = checkpoint_response.json()["items"]
    assert any(item["integrity_error"] == "payload_sha256 mismatch" for item in checkpoints)


def test_history_events_api_uses_stable_descending_order(client) -> None:
    response = client.post("/api/orchestrations/run", json=_default_run_payload())
    assert response.status_code == 200
    run_id = response.json()["id"]

    history_response = client.get(f"/api/orchestrations/{run_id}/history-events")
    assert history_response.status_code == 200
    events = history_response.json()["events"]
    ordering = [(event["occurred_at"], event["id"]) for event in events]
    assert ordering == sorted(ordering, reverse=True)


def test_queue_history_events_are_available_after_async_run(client) -> None:
    settings = get_settings()
    old_secret = settings.entitlement_secret
    old_required = settings.entitlement_required
    settings.entitlement_secret = "queue-ledger-secret"
    settings.entitlement_required = True
    token = sign_entitlement_token(secret="queue-ledger-secret", tier="pro", ttl_seconds=600)
    payload = {
        **_default_run_payload(),
        "team_subject": "platform-team",
        "requested_by": "queue-owner",
        "approval_actor": "release-manager",
        "approval_note": "Queue execution approved.",
    }
    response = client.post(
        "/api/orchestrations/queue/run",
        json=payload,
        headers={"X-Entitlement": token},
    )
    settings.entitlement_secret = old_secret
    settings.entitlement_required = old_required
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status_response = client.get(f"/api/orchestrations/queue/{job_id}")
    assert status_response.status_code == 200
    job = status_response.json()
    assert job["events"]
    assert job["team_subject"] == "platform-team"
    assert job["requested_by"] == "queue-owner"
    assert len(job["checkpoints"]) >= 2

    with SessionLocal() as db:
        ledger_events = (
            db.query(HistoryEvent)
            .filter(HistoryEvent.entity_type == "queue_job", HistoryEvent.entity_id == str(job_id))
            .order_by(HistoryEvent.occurred_at.asc(), HistoryEvent.id.asc())
            .all()
        )
    assert [event.event_type for event in ledger_events][:2] == ["queue.queued", "queue.started"]

    queue_history_response = client.get("/api/orchestrations/queue/history?team_subject=platform-team")
    assert queue_history_response.status_code == 200
    assert [item["id"] for item in queue_history_response.json()["items"]] == [job_id]

    history_response = client.get("/api/orchestrations/history?limit=1")
    assert history_response.status_code == 200
    ledger_integrity = history_response.json()["items"][0]["ledger_integrity"]
    assert ledger_integrity["integrity_status"] == "valid"
    assert ledger_integrity["event_count"] >= len(ledger_events)
