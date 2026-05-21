from datetime import datetime

from sqlalchemy import create_engine, text


def test_technical_analysis_workflow_persists_and_lists_history(client) -> None:
    create_response = client.post(
        "/api/analysis/technical",
        json={
            "issue_description": "Jenkins pipeline fails during deploy step.",
            "errors": ["Permission denied when pushing image to registry"],
            "logs": "deploy stage started\npermission denied for artifact upload\npipeline aborted",
            "code_snippets": ["docker push $IMAGE_TAG"],
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()

    assert created["id"] > 0
    assert "Observed technical issue" in created["output"]["problem_statement"]
    assert len(created["output"]["likely_causes"]) >= 1
    assert len(created["output"]["validation_steps"]) >= 3
    assert len(created["output"]["fix_options"]) >= 2
    assert len(created["output"]["risks"]) >= 1
    assert len(created["output"]["follow_up_tasks"]) >= 3

    history_response = client.get("/api/analysis/history")
    assert history_response.status_code == 200
    history = history_response.json()["items"]

    assert len(history) == 1
    assert history[0]["id"] == created["id"]
    assert history[0]["input"]["issue_description"] == "Jenkins pipeline fails during deploy step."
    assert history[0]["record_source"] == "user"
    assert history[0]["business_timezone"] == "Asia/Shanghai"
    assert history[0]["created_at"].endswith("Z")


def test_technical_analysis_uses_business_timezone_for_analysis_date(client, monkeypatch) -> None:
    from app.services import technical_analysis_service

    monkeypatch.setattr(technical_analysis_service, "utcnow_naive", lambda: datetime(2026, 5, 21, 16, 45, 36))

    response = client.post(
        "/api/analysis/technical",
        json={
            "issue_description": "Late incident",
            "errors": [],
            "logs": "late failure",
            "code_snippets": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_date"] == "2026-05-22"
    assert payload["created_at"] == "2026-05-21T16:45:36.000000Z"


def test_technical_analysis_history_filters_smoke_records_by_default(client) -> None:
    smoke = client.post(
        "/api/analysis/technical",
        headers={"X-Record-Source": "smoke_check"},
        json={
            "issue_description": "Smoke issue",
            "errors": ["timeout"],
            "logs": "error line",
            "code_snippets": ["kubectl get pods"],
        },
    )
    user = client.post(
        "/api/analysis/technical",
        json={
            "issue_description": "User issue",
            "errors": [],
            "logs": "user failure",
            "code_snippets": [],
        },
    )

    assert smoke.status_code == 200
    assert user.status_code == 200

    default_history = client.get("/api/analysis/history")
    assert default_history.status_code == 200
    assert [item["input"]["issue_description"] for item in default_history.json()["items"]] == ["User issue"]

    system_history = client.get("/api/analysis/history?include_system=true")
    assert system_history.status_code == 200
    assert [item["record_source"] for item in system_history.json()["items"]] == ["user", "smoke_check"]


def test_read_only_history_endpoints_do_not_write_agent_logs(client) -> None:
    plan = client.post(
        "/api/plans/daily",
        json={
            "tasks": ["Plan"],
            "meetings": [],
            "blockers": [],
            "priorities": ["Plan"],
        },
    )
    reflection = client.post(
        "/api/reflections/daily",
        json={
            "completed": ["Done"],
            "unfinished": [],
            "blockers": [],
            "mood_or_notes": "steady",
        },
    )
    analysis = client.post(
        "/api/analysis/technical",
        json={
            "issue_description": "Read only audit",
            "errors": [],
            "logs": "audit",
            "code_snippets": [],
        },
    )
    assert plan.status_code == 200
    assert reflection.status_code == 200
    assert analysis.status_code == 200

    engine = create_engine("sqlite:///./test_personal_agent.db", connect_args={"check_same_thread": False})
    with engine.begin() as connection:
        before = connection.execute(text("SELECT COUNT(*) FROM agent_run_logs")).scalar_one()

    assert client.get("/api/plans/history").status_code == 200
    assert client.get("/api/reflections/history").status_code == 200
    assert client.get("/api/analysis/history").status_code == 200

    with engine.begin() as connection:
        after = connection.execute(text("SELECT COUNT(*) FROM agent_run_logs")).scalar_one()

    assert after == before


def test_technical_analysis_rejects_empty_request(client) -> None:
    response = client.post(
        "/api/analysis/technical",
        json={
            "issue_description": "",
            "errors": [],
            "logs": "",
            "code_snippets": [],
        },
    )

    assert response.status_code == 422


def test_technical_analysis_history_returns_most_recent_first(client) -> None:
    first = client.post(
        "/api/analysis/technical",
        json={
            "issue_description": "First issue",
            "errors": [],
            "logs": "first failure log",
            "code_snippets": [],
        },
    )
    second = client.post(
        "/api/analysis/technical",
        json={
            "issue_description": "Second issue",
            "errors": [],
            "logs": "second failure log",
            "code_snippets": [],
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200

    history_response = client.get("/api/analysis/history")
    assert history_response.status_code == 200
    history = history_response.json()["items"]

    assert len(history) == 2
    assert history[0]["input"]["issue_description"] == "Second issue"
    assert history[1]["input"]["issue_description"] == "First issue"
