def test_daily_plan_rejects_invalid_tasks_shape(client) -> None:
    response = client.post(
        "/api/plans/daily",
        json={
            "tasks": "not-a-list",
            "meetings": [],
            "blockers": [],
            "priorities": [],
        },
    )
    assert response.status_code == 422


def test_daily_reflection_rejects_invalid_completed_shape(client) -> None:
    response = client.post(
        "/api/reflections/daily",
        json={
            "completed": "done",
            "unfinished": [],
            "blockers": [],
            "mood_or_notes": "",
        },
    )
    assert response.status_code == 422


def test_technical_analysis_rejects_whitespace_only_signals(client) -> None:
    response = client.post(
        "/api/analysis/technical",
        json={
            "issue_description": "   ",
            "errors": ["   "],
            "logs": "   ",
            "code_snippets": ["\n"],
        },
    )
    assert response.status_code == 422


def test_knowledge_list_sorted_by_updated_at(client) -> None:
    first = client.post(
        "/api/knowledge",
        json={"title": "Entry A", "content": "a", "tags": ["ops"]},
    )
    second = client.post(
        "/api/knowledge",
        json={"title": "Entry B", "content": "b", "tags": ["ops"]},
    )
    assert first.status_code == 200
    assert second.status_code == 200

    first_id = first.json()["id"]
    second_id = second.json()["id"]

    update_first = client.put(
        f"/api/knowledge/{first_id}",
        json={"content": "a-updated"},
    )
    assert update_first.status_code == 200

    listed = client.get("/api/knowledge")
    assert listed.status_code == 200
    ids = [item["id"] for item in listed.json()]
    assert ids == [first_id, second_id]


def test_templates_list_sorted_by_updated_at(client) -> None:
    first = client.post(
        "/api/templates",
        json={
            "name": "Template A",
            "description": "",
            "body": "body a",
            "tags": ["ops"],
        },
    )
    second = client.post(
        "/api/templates",
        json={
            "name": "Template B",
            "description": "",
            "body": "body b",
            "tags": ["ops"],
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    first_id = first.json()["id"]
    second_id = second.json()["id"]

    update_first = client.put(
        f"/api/templates/{first_id}",
        json={"description": "updated first"},
    )
    assert update_first.status_code == 200

    listed = client.get("/api/templates")
    assert listed.status_code == 200
    ids = [item["id"] for item in listed.json()]
    assert ids == [first_id, second_id]


def test_knowledge_create_rejects_blank_title_or_content(client) -> None:
    response = client.post(
        "/api/knowledge",
        json={"title": "   ", "content": "   ", "tags": []},
    )
    assert response.status_code == 422


def test_template_create_rejects_blank_name_or_body(client) -> None:
    response = client.post(
        "/api/templates",
        json={"name": "   ", "description": "", "body": "   ", "tags": []},
    )
    assert response.status_code == 422
