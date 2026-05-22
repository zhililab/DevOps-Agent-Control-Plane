def test_template_import_from_builtin_json_upserts(client) -> None:
    first = client.post(
        "/api/templates/import/json",
        json={"use_builtin": True, "upsert_by_name": True},
    )
    assert first.status_code == 200
    payload = first.json()
    assert payload["mode"] == "json"
    assert payload["total"] >= 22
    assert payload["imported"] >= 22

    second = client.post(
        "/api/templates/import/json",
        json={"use_builtin": True, "upsert_by_name": True},
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["updated"] >= 22

    listed = client.get("/api/templates")
    assert listed.status_code == 200
    assert len(listed.json()) >= 22


def test_template_import_from_builtin_sql(client) -> None:
    sql_response = client.get("/api/templates/init/sql")
    assert sql_response.status_code == 200
    assert "INSERT INTO prompt_templates" in sql_response.text

    imported = client.post(
        "/api/templates/import/sql",
        json={"sql": sql_response.text, "reset_existing": False, "use_builtin": False},
    )
    assert imported.status_code == 200
    payload = imported.json()
    assert payload["mode"] == "sql"
    assert payload["total"] >= 22
    assert payload["imported"] >= 22


def test_template_import_sql_rejects_non_insert(client) -> None:
    response = client.post(
        "/api/templates/import/sql",
        json={"sql": "DELETE FROM prompt_templates;", "use_builtin": False},
    )
    assert response.status_code == 422


def test_workflow_template_builtin_import_upserts(client) -> None:
    init_response = client.get("/api/orchestrations/templates/init/json")
    assert init_response.status_code == 200
    templates = init_response.json()
    assert len(templates) >= 12
    names = {item["name"] for item in templates}
    assert "Release Gate And Remote Deploy" in names
    assert "Query Performance Optimization" in names
    assert "Free Tier Smoke Check" in names

    first = client.post("/api/orchestrations/templates/import/builtin")
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["total"] >= 12
    assert first_payload["imported"] >= 12

    second = client.post("/api/orchestrations/templates/import/builtin")
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["total"] == first_payload["total"]
    assert second_payload["updated"] >= 12

    listed = client.get("/api/orchestrations/templates")
    assert listed.status_code == 200
    listed_items = listed.json()
    listed_names = {item["name"] for item in listed_items}
    assert names.issubset(listed_names)
    free_tier = next(item for item in listed_items if item["name"] == "Free Tier Smoke Check")
    assert len([step for step in free_tier["steps"] if step["enabled"]]) == 1
