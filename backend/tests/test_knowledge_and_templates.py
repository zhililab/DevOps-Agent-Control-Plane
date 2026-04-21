def test_knowledge_entry_crud_flow(client) -> None:
    create_response = client.post(
        "/api/knowledge",
        json={
            "title": "CI flake triage notes",
            "content": "Check recent runner changes and retry pattern.",
            "tags": ["devops", "ci"],
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    note_id = created["id"]
    assert created["tags"] == ["devops", "ci"]

    list_response = client.get("/api/knowledge")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    filtered_by_tag = client.get("/api/knowledge", params={"tag": "ci"})
    assert filtered_by_tag.status_code == 200
    assert len(filtered_by_tag.json()) == 1

    filtered_by_q = client.get("/api/knowledge", params={"q": "runner"})
    assert filtered_by_q.status_code == 200
    assert len(filtered_by_q.json()) == 1

    get_response = client.get(f"/api/knowledge/{note_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "CI flake triage notes"

    update_response = client.put(
        f"/api/knowledge/{note_id}",
        json={"content": "Check runner image + cache policy.", "tags": ["devops", "cache"]},
    )
    assert update_response.status_code == 200
    assert update_response.json()["tags"] == ["devops", "cache"]

    delete_response = client.delete(f"/api/knowledge/{note_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/knowledge/{note_id}")
    assert missing_response.status_code == 404


def test_prompt_template_crud_flow(client) -> None:
    create_response = client.post(
        "/api/templates",
        json={
            "name": "Incident Summary Template",
            "description": "Reusable post-incident summary format.",
            "body": "Context:\nImpact:\nRoot cause:\nActions:",
            "tags": ["incident", "report"],
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    template_id = created["id"]
    assert created["name"] == "Incident Summary Template"

    list_response = client.get("/api/templates")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    filtered_by_tag = client.get("/api/templates", params={"tag": "incident"})
    assert filtered_by_tag.status_code == 200
    assert len(filtered_by_tag.json()) == 1

    filtered_by_q = client.get("/api/templates", params={"q": "Root cause"})
    assert filtered_by_q.status_code == 200
    assert len(filtered_by_q.json()) == 1

    get_response = client.get(f"/api/templates/{template_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Incident Summary Template"

    update_response = client.put(
        f"/api/templates/{template_id}",
        json={"description": "Updated format", "tags": ["incident", "summary"]},
    )
    assert update_response.status_code == 200
    assert update_response.json()["tags"] == ["incident", "summary"]

    delete_response = client.delete(f"/api/templates/{template_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/templates/{template_id}")
    assert missing_response.status_code == 404


def test_knowledge_entry_tag_normalization_and_missing_routes(client) -> None:
    create_response = client.post(
        "/api/knowledge",
        json={
            "title": "  Incident postmortem notes  ",
            "content": "  Keep concise timeline and impact.  ",
            "tags": ["DevOps", " devops ", "  ", "Incident"],
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["title"] == "Incident postmortem notes"
    assert created["content"] == "Keep concise timeline and impact."
    assert created["tags"] == ["DevOps", "Incident"]

    filtered_by_tag = client.get("/api/knowledge", params={"tag": "incident"})
    assert filtered_by_tag.status_code == 200
    assert len(filtered_by_tag.json()) == 1

    missing_update_response = client.put("/api/knowledge/99999", json={"title": "Nope"})
    assert missing_update_response.status_code == 404
    assert missing_update_response.json()["detail"] == "Knowledge entry not found"

    missing_delete_response = client.delete("/api/knowledge/99999")
    assert missing_delete_response.status_code == 404
    assert missing_delete_response.json()["detail"] == "Knowledge entry not found"


def test_prompt_template_tag_normalization_and_missing_routes(client) -> None:
    create_response = client.post(
        "/api/templates",
        json={
            "name": "  Ops triage template ",
            "description": "  Useful for incidents.  ",
            "body": "  Problem:\nSignals:\nFix options:  ",
            "tags": ["Runbook", " runbook ", "OnCall", ""],
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["name"] == "Ops triage template"
    assert created["description"] == "Useful for incidents."
    assert created["body"] == "Problem:\nSignals:\nFix options:"
    assert created["tags"] == ["Runbook", "OnCall"]

    filtered_by_tag = client.get("/api/templates", params={"tag": "oncall"})
    assert filtered_by_tag.status_code == 200
    assert len(filtered_by_tag.json()) == 1

    missing_update_response = client.put("/api/templates/99999", json={"name": "Nope"})
    assert missing_update_response.status_code == 404
    assert missing_update_response.json()["detail"] == "Prompt template not found"

    missing_delete_response = client.delete("/api/templates/99999")
    assert missing_delete_response.status_code == 404
    assert missing_delete_response.json()["detail"] == "Prompt template not found"
