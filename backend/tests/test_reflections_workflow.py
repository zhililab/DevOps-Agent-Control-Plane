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
