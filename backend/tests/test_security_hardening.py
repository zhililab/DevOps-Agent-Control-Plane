from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.security_utils import sanitize_for_log


def test_log_sanitization_redacts_sensitive_pairs_and_bearer_token() -> None:
    raw = "password=abc123 token:xyz authorization=Bearer super-secret-token"
    sanitized = sanitize_for_log(raw, max_chars=500)

    assert "abc123" not in sanitized
    assert "xyz" not in sanitized
    assert "super-secret-token" not in sanitized
    assert "password=<redacted>" in sanitized
    assert "token=<redacted>" in sanitized
    assert "authorization=<redacted>" in sanitized


def test_rate_limit_returns_429_when_exceeded(monkeypatch) -> None:
    monkeypatch.setenv("APP_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("APP_RATE_LIMIT_MAX_REQUESTS", "2")
    monkeypatch.setenv("APP_RATE_LIMIT_WINDOW_SECONDS", "60")

    get_settings.cache_clear()
    app = create_app()

    with TestClient(app) as client:
        r1 = client.get("/api/templates/init/json")
        r2 = client.get("/api/templates/init/json")
        r3 = client.get("/api/templates/init/json")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.json()["detail"] == "Too many requests. Please retry later."

    get_settings.cache_clear()


def test_technical_analysis_rejects_excessive_logs(client) -> None:
    response = client.post(
        "/api/analysis/technical",
        json={
            "issue_description": "test",
            "logs": "x" * 10001,
            "errors": [],
            "code_snippets": [],
        },
    )

    assert response.status_code == 422
