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
