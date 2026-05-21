from datetime import datetime


def test_daily_reflection_workflow_persists_and_lists_history(client) -> None:
    create_response = client.post(
        "/api/reflections/daily",
        json={
            "completed": ["Closed CI incident"],
            "unfinished": ["Finalize release checklist"],
            "blockers": ["Waiting for security approval"],
            "mood_or_notes": "Focused but blocked by approvals.",
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()

    assert created["id"] > 0
    assert "Completed 1 item(s)" in created["summary"]["day_summary"]
    assert created["summary"]["unfinished_items"] == ["Finalize release checklist"]
    assert len(created["summary"]["pattern_hints"]) >= 1
    assert len(created["summary"]["tomorrow_suggestions"]) >= 2

    history_response = client.get("/api/reflections/history")
    assert history_response.status_code == 200
    history = history_response.json()["items"]

    assert len(history) == 1
    assert history[0]["id"] == created["id"]
    assert history[0]["input"]["completed"] == ["Closed CI incident"]
    assert history[0]["record_source"] == "user"
    assert history[0]["business_timezone"] == "Asia/Shanghai"
    assert history[0]["created_at"].endswith("Z")


def test_daily_reflection_uses_business_timezone_for_entry_date(client, monkeypatch) -> None:
    from app.services import reflection_service

    monkeypatch.setattr(reflection_service, "utcnow_naive", lambda: datetime(2026, 5, 21, 16, 45, 36))

    response = client.post(
        "/api/reflections/daily",
        json={
            "completed": ["Late work"],
            "unfinished": [],
            "blockers": [],
            "mood_or_notes": "steady",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["entry_date"] == "2026-05-22"
    assert payload["created_at"] == "2026-05-21T16:45:36.000000Z"


def test_daily_reflection_history_filters_smoke_records_by_default(client) -> None:
    smoke = client.post(
        "/api/reflections/daily",
        headers={"X-Record-Source": "smoke_check"},
        json={
            "completed": ["Done"],
            "unfinished": ["Todo"],
            "blockers": ["Dependency"],
            "mood_or_notes": "steady",
        },
    )
    user = client.post(
        "/api/reflections/daily",
        json={
            "completed": ["User done"],
            "unfinished": [],
            "blockers": [],
            "mood_or_notes": "good",
        },
    )

    assert smoke.status_code == 200
    assert user.status_code == 200

    default_history = client.get("/api/reflections/history")
    assert default_history.status_code == 200
    assert [item["input"]["completed"][0] for item in default_history.json()["items"]] == ["User done"]

    system_history = client.get("/api/reflections/history?include_system=true")
    assert system_history.status_code == 200
    assert [item["record_source"] for item in system_history.json()["items"]] == ["user", "smoke_check"]


def test_daily_reflection_defaults_when_input_is_sparse(client) -> None:
    create_response = client.post(
        "/api/reflections/daily",
        json={
            "completed": [],
            "unfinished": [],
            "blockers": [],
            "mood_or_notes": "",
        },
    )

    assert create_response.status_code == 200
    payload = create_response.json()

    assert "No completed items were captured today." in payload["summary"]["day_summary"]
    assert payload["summary"]["unfinished_items"] == []
    assert payload["summary"]["pattern_hints"] == ["Steady day pattern; continue with the same planning cadence."]
    assert len(payload["summary"]["tomorrow_suggestions"]) >= 1


def test_daily_reflection_history_returns_most_recent_first(client) -> None:
    first = client.post(
        "/api/reflections/daily",
        json={
            "completed": ["Task A done"],
            "unfinished": ["Task A carry-over"],
            "blockers": [],
            "mood_or_notes": "good",
        },
    )
    second = client.post(
        "/api/reflections/daily",
        json={
            "completed": ["Task B done"],
            "unfinished": ["Task B carry-over"],
            "blockers": [],
            "mood_or_notes": "good",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200

    history_response = client.get("/api/reflections/history")
    assert history_response.status_code == 200
    history = history_response.json()["items"]

    assert len(history) == 2
    assert history[0]["input"]["completed"] == ["Task B done"]
    assert history[1]["input"]["completed"] == ["Task A done"]
