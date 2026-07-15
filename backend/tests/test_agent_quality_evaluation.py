import json

from app.config import get_settings


class _FakeProviderResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "model": "doubao-test-model",
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "decision": "approve",
                                "confidence": 0.91,
                                "rationale": "Passing checks and a bounded documentation change support approval.",
                                "risks": ["Keep the evidence packet with the release."],
                            }
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }


class _FakeProviderClient:
    last_headers: dict[str, str] = {}
    last_trust_env: bool | None = None

    def __init__(self, *, timeout: float, trust_env: bool) -> None:
        self.timeout = timeout
        self.__class__.last_trust_env = trust_env

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def post(self, url: str, *, headers: dict[str, str], json: dict) -> _FakeProviderResponse:
        assert url.endswith("/chat/completions")
        assert json["temperature"] == 0
        self.__class__.last_headers = headers
        return _FakeProviderResponse()


def _enable_fake_provider(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "volcengine_ark_coding_plan")
    monkeypatch.setattr(settings, "llm_base_url", "https://ark.cn-beijing.volces.com/api/coding/v3")
    monkeypatch.setattr(settings, "llm_api_key", "rotated-test-key")
    monkeypatch.setattr(settings, "llm_model", "doubao-test-model")
    monkeypatch.setattr(settings, "llm_prompt_version", "pr-ci-gate.test-v1")
    monkeypatch.setattr(settings, "llm_input_cost_per_million_usd", 1.0)
    monkeypatch.setattr(settings, "llm_output_cost_per_million_usd", 2.0)
    monkeypatch.setattr("app.services.llm_provider.httpx.Client", _FakeProviderClient)


def test_fixed_dataset_contains_25_versioned_cases_and_rules_baseline_is_reproducible(client) -> None:
    cases_response = client.get("/api/evaluations/cases")
    assert cases_response.status_code == 200
    dataset = cases_response.json()
    assert dataset["dataset_version"] == "pr-ci-gate.v1.25"
    assert len(dataset["items"]) == 25
    assert [item["id"] for item in dataset["items"][:3]] == [
        "docs-only-pass",
        "unit-test-pass",
        "comment-cleanup",
    ]

    run_response = client.post("/api/evaluations/runs", json={"mode": "deterministic", "case_ids": []})
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["case_count"] == 25
    assert run["correct_count"] == 25
    assert run["accuracy"] == 1.0
    assert run["false_positive_count"] == 0
    assert run["false_negative_count"] == 0
    assert run["model"] == "release-gate-rules.v1"

    latest = client.get("/api/evaluations/runs/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == run["id"]


def test_production_evaluation_mutations_require_dedicated_write_access(client) -> None:
    settings = get_settings()
    old_environment = settings.environment
    old_write_secret = settings.evaluation_write_secret
    try:
        settings.environment = "production"
        settings.evaluation_write_secret = "quality-write-secret"

        status = client.get("/api/evaluations/provider-status")
        assert status.status_code == 200
        assert status.json()["write_protected"] is True
        assert "quality-write-secret" not in json.dumps(status.json())

        missing = client.post(
            "/api/evaluations/runs",
            json={"mode": "deterministic", "case_ids": ["docs-only-pass"]},
        )
        assert missing.status_code == 401
        assert missing.json()["detail"] == "Missing evaluation write access."

        invalid = client.post(
            "/api/evaluations/runs",
            headers={"X-Evaluation-Access": "wrong-secret"},
            json={"mode": "deterministic", "case_ids": ["docs-only-pass"]},
        )
        assert invalid.status_code == 401
        assert invalid.json()["detail"] == "Invalid evaluation write access."

        allowed = client.post(
            "/api/evaluations/runs",
            headers={"X-Evaluation-Access": "quality-write-secret"},
            json={"mode": "deterministic", "case_ids": ["docs-only-pass"]},
        )
        assert allowed.status_code == 200
        result_id = allowed.json()["results"][0]["id"]

        feedback = client.post(
            "/api/evaluations/feedback",
            json={
                "evaluation_case_result_id": result_id,
                "verdict": "accepted",
                "actor": "security-reviewer",
            },
        )
        assert feedback.status_code == 401

        measurement = client.post(
            "/api/evaluations/pilot-measurements",
            json={
                "subject": "security-user",
                "team_subject": "platform-team",
                "metric": "review_minutes",
                "phase": "pilot",
                "value": 1,
                "unit": "minutes",
                "sample_size": 1,
                "source": "observed",
            },
        )
        assert measurement.status_code == 401
    finally:
        settings.environment = old_environment
        settings.evaluation_write_secret = old_write_secret


def test_orchestration_model_observation_is_explicit_opt_in(client, monkeypatch) -> None:
    _enable_fake_provider(monkeypatch)
    payload = {
        "entry_source": "quality-default-off-test",
        "steps": [{"step_name": "AI PR Release Gate", "agent_type": "reviewer", "enabled": True}],
        "release_gate_input": {
            "pr_url": "https://github.example/acme/app/pull/200",
            "pr_diff_summary": "Documentation-only release note.",
            "ci_log_summary": "All checks passed.",
            "target_environment": "documentation",
            "change_risk": "No runtime change.",
        },
        "approval_confirmed": True,
    }

    response = client.post("/api/orchestrations/run", json=payload)
    assert response.status_code == 200
    orchestration_id = response.json()["id"]
    invocations = client.get(
        f"/api/evaluations/invocations?orchestration_id={orchestration_id}"
    ).json()["items"]
    assert invocations == []


def test_live_provider_persists_model_prompt_tokens_latency_and_cost_without_api_key(client, monkeypatch) -> None:
    _enable_fake_provider(monkeypatch)

    status_response = client.get("/api/evaluations/provider-status")
    assert status_response.status_code == 200
    assert status_response.json() == {
        "enabled": True,
        "configured": True,
        "provider": "volcengine_ark_coding_plan",
        "model": "doubao-test-model",
        "prompt_version": "pr-ci-gate.test-v1",
        "base_url_host": "ark.cn-beijing.volces.com",
        "write_protected": False,
        "deterministic_gate_remains_authoritative": True,
    }

    run_response = client.post(
        "/api/evaluations/runs",
        json={"mode": "live", "case_ids": ["docs-only-pass"]},
    )
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["provider"] == "volcengine_ark_coding_plan"
    assert run["model"] == "doubao-test-model"
    assert run["prompt_version"] == "pr-ci-gate.test-v1"
    assert run["input_tokens"] == 100
    assert run["output_tokens"] == 50
    assert run["estimated_cost_usd"] == 0.0002
    assert run["results"][0]["actual_decision"] == "approve"

    invocations_response = client.get("/api/evaluations/invocations")
    assert invocations_response.status_code == 200
    serialized = json.dumps(invocations_response.json())
    assert "rotated-test-key" not in serialized
    invocation = invocations_response.json()["items"][0]
    assert invocation["input_tokens"] == 100
    assert invocation["output_tokens"] == 50
    assert invocation["estimated_cost_usd"] == 0.0002
    assert _FakeProviderClient.last_headers["Authorization"] == "Bearer rotated-test-key"
    assert _FakeProviderClient.last_trust_env is False


def test_orchestration_records_optional_model_observation_without_changing_deterministic_gate(client, monkeypatch) -> None:
    _enable_fake_provider(monkeypatch)
    payload = {
        "entry_source": "quality-test",
        "steps": [{"step_name": "AI PR Release Gate", "agent_type": "reviewer", "enabled": True}],
        "release_gate_input": {
            "pr_url": "https://github.example/acme/app/pull/201",
            "pr_diff_summary": "Documentation-only release note.",
            "ci_log_summary": "All checks passed.",
            "target_environment": "documentation",
            "change_risk": "No runtime change.",
        },
        "approval_confirmed": True,
        "use_llm_provider": True,
    }
    response = client.post("/api/orchestrations/run", json=payload)
    assert response.status_code == 200
    orchestration = response.json()
    assert orchestration["policy_gate"]["decision"] == "approve"

    invocations = client.get(f"/api/evaluations/invocations?orchestration_id={orchestration['id']}").json()["items"]
    assert len(invocations) == 1
    assert invocations[0]["decision"] == "approve"
    assert invocations[0]["orchestration_id"] == orchestration["id"]


def test_feedback_summary_uses_latest_human_acceptance_and_correction(client) -> None:
    run = client.post(
        "/api/evaluations/runs",
        json={"mode": "deterministic", "case_ids": ["docs-only-pass", "prod-feature-review"]},
    ).json()
    first, second = run["results"]

    accepted = client.post(
        "/api/evaluations/feedback",
        json={
            "evaluation_case_result_id": first["id"],
            "verdict": "accepted",
            "actor": "sre-reviewer",
            "note": "Decision matches the expected low-risk gate.",
        },
    )
    assert accepted.status_code == 200
    corrected = client.post(
        "/api/evaluations/feedback",
        json={
            "evaluation_case_result_id": second["id"],
            "verdict": "corrected",
            "corrected_decision": "needs human review",
            "actor": "release-manager",
        },
    )
    assert corrected.status_code == 200

    summary = client.get("/api/evaluations/feedback-summary").json()
    assert summary["total"] == 2
    assert summary["accepted"] == 1
    assert summary["corrected"] == 1
    assert summary["acceptance_rate"] == 0.5
    assert summary["reviewed_accuracy"] == 1.0
    assert summary["false_positive_rate"] == 0.0
    assert summary["false_negative_rate"] == 0.0


def test_measured_pilot_comparison_keeps_baseline_and_pilot_separate_from_estimated_roi(client) -> None:
    baseline = client.post(
        "/api/evaluations/pilot-measurements",
        json={
            "subject": "interview-user",
            "team_subject": "platform-team",
            "metric": "review_minutes",
            "phase": "baseline",
            "value": 30,
            "unit": "minutes",
            "sample_size": 4,
            "source": "observed",
        },
    )
    pilot = client.post(
        "/api/evaluations/pilot-measurements",
        json={
            "subject": "interview-user",
            "team_subject": "platform-team",
            "metric": "review_minutes",
            "phase": "pilot",
            "value": 12,
            "unit": "minutes",
            "sample_size": 4,
            "source": "observed",
        },
    )
    assert baseline.status_code == 200
    assert pilot.status_code == 200

    comparison = client.get(
        "/api/evaluations/pilot-comparison?subject=interview-user&team_subject=platform-team"
    ).json()
    assert comparison["source"] == "measured"
    assert comparison["estimated_roi_remains_separate"] is True
    assert comparison["metrics"] == [
        {
            "metric": "review_minutes",
            "unit": "minutes",
            "baseline_value": 30.0,
            "pilot_value": 12.0,
            "absolute_change": -18.0,
            "improvement_rate": 0.6,
            "baseline_sample_size": 4,
            "pilot_sample_size": 4,
        }
    ]
