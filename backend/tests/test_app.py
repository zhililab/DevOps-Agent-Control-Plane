from app.main import create_app


def test_app_startup_configures_title() -> None:
    app = create_app()
    assert app.title == "Personal Agent Assistant API"


def test_health_endpoint_returns_ok(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
