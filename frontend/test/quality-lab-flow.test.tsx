import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import EvaluationPage from "@/app/evaluation/page";


const mocks = vi.hoisted(() => ({
  getLlmProviderStatus: vi.fn(),
  listEvaluationCases: vi.fn(),
  getLatestEvaluationRun: vi.fn(),
  getDecisionFeedbackSummary: vi.fn(),
  listLlmInvocations: vi.fn(),
  getPilotComparison: vi.fn(),
  runEvaluation: vi.fn(),
  createDecisionFeedback: vi.fn(),
  createPilotMeasurement: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ apiClient: mocks }));

const run = {
  id: 1,
  dataset_version: "pr-ci-gate.v1.25",
  provider: "volcengine_ark",
  model: "doubao-test-model",
  prompt_version: "pr-ci-gate.v1",
  mode: "deterministic",
  status: "completed",
  case_count: 1,
  correct_count: 1,
  false_positive_count: 0,
  false_negative_count: 0,
  accuracy: 1,
  average_latency_ms: 40,
  input_tokens: 100,
  output_tokens: 20,
  estimated_cost_usd: 0.0001,
  created_at: "2026-07-15T00:00:00Z",
  completed_at: "2026-07-15T00:00:01Z",
  results: [
    {
      id: 10,
      case_id: "docs-only-pass",
      expected_decision: "approve",
      actual_decision: "approve",
      is_correct: true,
      confidence: 0.92,
      rationale: "Passing evidence.",
      latency_ms: 40,
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getLlmProviderStatus.mockResolvedValue({
    enabled: true,
    configured: true,
    provider: "volcengine_ark",
    model: "doubao-test-model",
    prompt_version: "pr-ci-gate.v1",
    base_url_host: "ark.cn-beijing.volces.com",
    write_protected: false,
    deterministic_gate_remains_authoritative: true,
  });
  mocks.listEvaluationCases.mockResolvedValue({
    dataset_version: "pr-ci-gate.v1.25",
    items: [
      {
        id: "docs-only-pass",
        name: "Documentation-only change with passing CI",
        category: "low-risk",
        expected_decision: "approve",
        release_gate_input: {
          pr_url: "https://github.example/acme/app/pull/101",
          pr_diff_summary: "README only",
          ci_log_summary: "passed",
          target_environment: "documentation",
          change_risk: "none",
        },
        rationale: "Low risk.",
      },
    ],
  });
  mocks.getLatestEvaluationRun.mockResolvedValue(null);
  mocks.getDecisionFeedbackSummary.mockResolvedValue({
    total: 0,
    accepted: 0,
    rejected: 0,
    corrected: 0,
    acceptance_rate: 0,
    correction_rate: 0,
    reviewed_accuracy: 0,
    false_positive_rate: 0,
    false_negative_rate: 0,
    recent: [],
  });
  mocks.listLlmInvocations.mockResolvedValue({ items: [] });
  mocks.getPilotComparison.mockResolvedValue({
    subject: "demo-user",
    team_subject: "demo-team",
    source: "not_configured",
    metrics: [],
    measured_value_summary: "Record both phases.",
    estimated_roi_remains_separate: true,
  });
  mocks.runEvaluation.mockResolvedValue(run);
  mocks.createDecisionFeedback.mockResolvedValue({ id: 1 });
  mocks.createPilotMeasurement.mockResolvedValue({ id: 1 });
});

describe("quality lab", () => {
  test("explains protected feedback actions instead of silently disabling them", async () => {
    mocks.getLlmProviderStatus.mockResolvedValueOnce({
      enabled: true,
      configured: true,
      provider: "volcengine_ark",
      model: "doubao-test-model",
      prompt_version: "pr-ci-gate.v1",
      base_url_host: "ark.cn-beijing.volces.com",
      write_protected: true,
      deterministic_gate_remains_authoritative: true,
    });
    mocks.getLatestEvaluationRun.mockResolvedValueOnce(run);

    render(<EvaluationPage />);

    const accessInput = await screen.findByLabelText("Access key");
    const acceptButton = await screen.findByRole("button", { name: "Accept" });
    expect(acceptButton).toBeEnabled();

    fireEvent.click(acceptButton);

    expect(await screen.findByText("Enter Quality Write Access to save review evidence.")).toBeInTheDocument();
    expect(accessInput).toHaveFocus();
    expect(mocks.createDecisionFeedback).not.toHaveBeenCalled();
  });

  test("runs fixed evaluation and records explicit human feedback", async () => {
    render(<EvaluationPage />);

    expect(await screen.findByRole("heading", { name: "Agent Quality Lab" })).toBeInTheDocument();
    expect(screen.getByText("QUALITY EVIDENCE")).toBeInTheDocument();
    expect(await screen.findByText("doubao-test-model · pr-ci-gate.v1")).toBeInTheDocument();
    expect(screen.getByText("pr-ci-gate.v1.25 · 1 versioned cases")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Run Rules Baseline" }));
    expect(await screen.findByText("Documentation-only change with passing CI")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(mocks.runEvaluation).toHaveBeenCalledWith("deterministic", [], "");

    mocks.getDecisionFeedbackSummary.mockResolvedValueOnce({
      total: 1,
      accepted: 1,
      rejected: 0,
      corrected: 0,
      acceptance_rate: 1,
      correction_rate: 0,
      reviewed_accuracy: 1,
      false_positive_rate: 0,
      false_negative_rate: 0,
      recent: [
        {
          id: 1,
          evaluation_case_result_id: 10,
          orchestration_id: null,
          verdict: "accepted",
          corrected_decision: "",
          actor: "quality-reviewer",
          note: "",
          created_at: "2026-07-16T00:00:00Z",
        },
      ],
    });
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(mocks.createDecisionFeedback).toHaveBeenCalledWith(
      expect.objectContaining({
        evaluation_case_result_id: 10,
        verdict: "accepted",
      }),
      ""
    ));
    expect(await screen.findByText("1 accepted")).toBeInTheDocument();
    expect(screen.getByText("Saved: accepted")).toBeInTheDocument();
  });

  test("records observed baseline measurement separately from estimated ROI", async () => {
    render(<EvaluationPage />);
    await screen.findByText("Record both phases.");

    mocks.getPilotComparison.mockResolvedValueOnce({
      subject: "demo-user",
      team_subject: "demo-team",
      source: "measured",
      metrics: [
        {
          metric: "review_minutes",
          unit: "minutes",
          baseline_value: 30,
          pilot_value: 12,
          absolute_change: -18,
          improvement_rate: 0.6,
          baseline_sample_size: 1,
          pilot_sample_size: 1,
        },
      ],
      measured_value_summary: "Measured.",
      estimated_roi_remains_separate: true,
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Observation" }));
    await waitFor(() => expect(mocks.createPilotMeasurement).toHaveBeenCalledWith(
      expect.objectContaining({
        metric: "review_minutes",
        phase: "baseline",
        value: 30,
        source: "observed",
      }),
      ""
    ));
    expect(await screen.findByText("30 → 12")).toBeInTheDocument();
    expect(screen.getByText("60% improvement · minutes")).toBeInTheDocument();
  });

  test("keeps protected write access in page memory and forwards it only in request headers", async () => {
    mocks.getLlmProviderStatus.mockResolvedValueOnce({
      enabled: true,
      configured: true,
      provider: "volcengine_ark_coding_plan",
      model: "doubao-test-model",
      prompt_version: "pr-ci-gate.v1",
      base_url_host: "ark.cn-beijing.volces.com",
      write_protected: true,
      deterministic_gate_remains_authoritative: true,
    });
    render(<EvaluationPage />);

    const accessInput = await screen.findByLabelText("Access key");
    const rulesButton = screen.getByRole("button", { name: "Run Rules Baseline" });
    expect(rulesButton).toBeEnabled();

    fireEvent.change(accessInput, { target: { value: "quality-write-secret" } });
    fireEvent.click(rulesButton);

    await waitFor(() => expect(mocks.runEvaluation).toHaveBeenCalledWith(
      "deterministic",
      [],
      "quality-write-secret"
    ));
    expect(window.localStorage.getItem("quality-write-secret")).toBeNull();
  });
});
