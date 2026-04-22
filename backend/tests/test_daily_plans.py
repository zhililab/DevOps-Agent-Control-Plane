from sqlalchemy import create_engine, text


def test_daily_plan_workflow_persists_and_lists_history(client) -> None:
    create_response = client.post(
        "/api/plans/daily",
        json={
            "tasks": ["Fix CI flake", "Prepare release notes"],
            "meetings": ["10:30 Platform sync"],
            "blockers": ["Need infra approval"],
            "priorities": ["Fix CI flake"],
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()

    assert created["id"] > 0
    assert created["plan"]["top_priorities"][0] == "Fix CI flake"
    assert len(created["plan"]["recommended_order"]) >= 2
    assert any("Blocker risk" in item for item in created["plan"]["risks_and_reminders"])
    assert len(created["plan"]["next_actions"]) >= 2
    assert "Planned" in created["plan"]["status_summary"]

    history_response = client.get("/api/plans/history")
    assert history_response.status_code == 200
    history = history_response.json()["items"]

    assert len(history) == 1
    assert history[0]["id"] == created["id"]
    assert history[0]["context"]["tasks"][0] == "Fix CI flake"


def test_daily_plan_still_succeeds_when_agent_log_table_missing(client) -> None:
    engine = create_engine("sqlite:///./test_personal_agent.db", connect_args={"check_same_thread": False})
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS agent_run_logs"))

    response = client.post(
        "/api/plans/daily",
        json={
            "tasks": ["Smoke task"],
            "meetings": ["Smoke meeting"],
            "blockers": ["None"],
            "priorities": ["Smoke task"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "status_summary" in payload["plan"]


def test_daily_plan_empty_context_has_deterministic_defaults(client) -> None:
    response = client.post(
        "/api/plans/daily",
        json={
            "tasks": [],
            "meetings": [],
            "blockers": [],
            "priorities": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["plan"]["top_priorities"] == ["Clarify one meaningful outcome for today"]
    assert payload["plan"]["recommended_order"] == [
        "Clarify one meaningful outcome for today",
        "Define top priority",
        "Plan one focused work block",
        "Review end-of-day status",
    ]
    assert payload["plan"]["risks_and_reminders"] == [
        "No major risks captured. Keep monitoring for hidden blockers."
    ]
    assert len(payload["plan"]["next_actions"]) >= 3


def test_daily_plan_history_returns_most_recent_first(client) -> None:
    first = client.post(
        "/api/plans/daily",
        json={
            "tasks": ["Task A"],
            "meetings": [],
            "blockers": [],
            "priorities": ["Task A"],
        },
    )
    second = client.post(
        "/api/plans/daily",
        json={
            "tasks": ["Task B"],
            "meetings": [],
            "blockers": [],
            "priorities": ["Task B"],
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200

    history_response = client.get("/api/plans/history")
    assert history_response.status_code == 200
    history = history_response.json()["items"]

    assert len(history) == 2
    assert history[0]["context"]["tasks"] == ["Task B"]
    assert history[1]["context"]["tasks"] == ["Task A"]
