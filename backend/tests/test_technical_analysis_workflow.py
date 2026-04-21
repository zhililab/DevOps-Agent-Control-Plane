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
