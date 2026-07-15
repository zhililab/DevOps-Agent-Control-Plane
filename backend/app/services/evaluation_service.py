from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    DecisionFeedback,
    EvaluationCaseResult,
    EvaluationRun,
    LlmInvocation,
    PilotMeasurement,
    WorkflowOrchestration,
)
from app.schemas import (
    DecisionFeedbackCreate,
    DecisionFeedbackRead,
    DecisionFeedbackSummaryResponse,
    EvaluationCaseListResponse,
    EvaluationCaseRead,
    EvaluationCaseResultRead,
    EvaluationRunRead,
    EvaluationRunRequest,
    LlmInvocationListResponse,
    PilotComparisonResponse,
    PilotMeasurementCreate,
    PilotMeasurementRead,
    PilotMetricComparison,
    ReleaseGateDecision,
    ReleaseGatePrCiInput,
)
from app.services.llm_provider import invoke_release_gate_model, provider_status, to_invocation_read
from app.services.security_utils import sanitize_for_log
from app.time_utils import utcnow_naive


EVALUATION_DATASET_PATH = Path(__file__).resolve().parents[1] / "bootstrap" / "pr_ci_eval_cases_v1.json"
METRIC_ORDER = (
    "review_minutes",
    "audit_minutes",
    "release_lead_time_minutes",
    "incidents",
    "rollback_minutes",
)


def list_evaluation_cases() -> EvaluationCaseListResponse:
    raw = json.loads(EVALUATION_DATASET_PATH.read_text(encoding="utf-8"))
    return EvaluationCaseListResponse(
        dataset_version=str(raw.get("dataset_version") or "pr-ci-gate.v1"),
        items=[EvaluationCaseRead.model_validate(item) for item in raw.get("items", [])],
    )


def run_evaluation(db: Session, payload: EvaluationRunRequest) -> EvaluationRunRead:
    dataset = list_evaluation_cases()
    case_by_id = {item.id: item for item in dataset.items}
    selected = dataset.items if not payload.case_ids else []
    if payload.case_ids:
        unknown = [case_id for case_id in payload.case_ids if case_id not in case_by_id]
        if unknown:
            raise HTTPException(status_code=422, detail=f"Unknown evaluation case(s): {', '.join(unknown)}")
        selected = [case_by_id[case_id] for case_id in payload.case_ids]
    if not selected:
        raise HTTPException(status_code=422, detail="Select at least one evaluation case.")

    settings = get_settings()
    status = provider_status(settings)
    if payload.mode == "live" and not bool(status["configured"]):
        raise HTTPException(status_code=503, detail="Live LLM provider is not configured.")

    record = EvaluationRun(
        dataset_version=dataset.dataset_version,
        provider=str(status["provider"]) if payload.mode == "live" else "deterministic",
        model=str(status["model"]) if payload.mode == "live" else "release-gate-rules.v1",
        prompt_version=str(status["prompt_version"]) if payload.mode == "live" else "release-gate-rules.v1",
        mode=payload.mode,
        status="running",
        case_count=len(selected),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    correct = 0
    false_positive = 0
    false_negative = 0
    total_latency = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost_microusd = 0
    has_provider_failure = False

    for case in selected:
        invocation_id: int | None = None
        confidence = 1.0
        rationale = "Deterministic release-gate rules evaluated fixed PR/CI evidence."
        latency_ms = 0
        if payload.mode == "live":
            decision = invoke_release_gate_model(
                db,
                case.release_gate_input,
                evaluation_run_id=record.id,
                evaluation_case_id=case.id,
                settings=settings,
            )
            actual = decision.decision
            confidence = decision.confidence
            rationale = decision.rationale
            invocation_id = decision.invocation_id
            invocation = db.get(LlmInvocation, invocation_id)
            if invocation is not None:
                latency_ms = invocation.latency_ms
                total_input_tokens += invocation.input_tokens
                total_output_tokens += invocation.output_tokens
                total_cost_microusd += invocation.estimated_cost_microusd
            if decision.status != "success":
                has_provider_failure = True
        else:
            actual = deterministic_release_gate_decision(case.release_gate_input)

        is_correct = actual == case.expected_decision
        correct += int(is_correct)
        false_positive += int(case.expected_decision == "approve" and actual != "approve")
        false_negative += int(case.expected_decision != "approve" and actual == "approve")
        total_latency += latency_ms
        db.add(
            EvaluationCaseResult(
                evaluation_run_id=record.id,
                invocation_id=invocation_id,
                case_id=case.id,
                expected_decision=case.expected_decision,
                actual_decision=actual,
                is_correct=is_correct,
                confidence=confidence,
                rationale=sanitize_for_log(rationale, max_chars=2000),
                latency_ms=latency_ms,
            )
        )

    record.status = "partial_failure" if has_provider_failure else "completed"
    record.correct_count = correct
    record.false_positive_count = false_positive
    record.false_negative_count = false_negative
    record.accuracy = round(correct / len(selected), 4)
    record.average_latency_ms = round(total_latency / len(selected))
    record.input_tokens = total_input_tokens
    record.output_tokens = total_output_tokens
    record.estimated_cost_microusd = total_cost_microusd
    record.completed_at = utcnow_naive()
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_evaluation_run_read(db, record)


def get_latest_evaluation_run(db: Session) -> EvaluationRunRead | None:
    record = db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc(), EvaluationRun.id.desc()).first()
    return _to_evaluation_run_read(db, record) if record is not None else None


def list_llm_invocations(
    db: Session,
    *,
    orchestration_id: int | None = None,
    limit: int = 50,
) -> LlmInvocationListResponse:
    query = db.query(LlmInvocation)
    if orchestration_id is not None:
        query = query.filter(LlmInvocation.orchestration_id == orchestration_id)
    records = query.order_by(LlmInvocation.created_at.desc(), LlmInvocation.id.desc()).limit(limit).all()
    return LlmInvocationListResponse(items=[to_invocation_read(item) for item in records])


def create_decision_feedback(db: Session, payload: DecisionFeedbackCreate) -> DecisionFeedbackRead:
    if payload.evaluation_case_result_id is not None and db.get(EvaluationCaseResult, payload.evaluation_case_result_id) is None:
        raise HTTPException(status_code=404, detail="Evaluation case result not found.")
    if payload.orchestration_id is not None and db.get(WorkflowOrchestration, payload.orchestration_id) is None:
        raise HTTPException(status_code=404, detail="Orchestration not found.")
    record = DecisionFeedback(
        evaluation_case_result_id=payload.evaluation_case_result_id,
        orchestration_id=payload.orchestration_id,
        verdict=payload.verdict,
        corrected_decision=payload.corrected_decision or "",
        actor=sanitize_for_log(payload.actor, max_chars=120) or "reviewer",
        note=sanitize_for_log(payload.note, max_chars=2000),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_feedback_read(record)


def get_feedback_summary(db: Session) -> DecisionFeedbackSummaryResponse:
    records = db.query(DecisionFeedback).order_by(DecisionFeedback.created_at.desc(), DecisionFeedback.id.desc()).all()
    total = len(records)
    accepted = sum(item.verdict == "accepted" for item in records)
    rejected = sum(item.verdict == "rejected" for item in records)
    corrected = sum(item.verdict == "corrected" for item in records)

    latest_by_target: dict[tuple[str, int], DecisionFeedback] = {}
    for item in records:
        if item.evaluation_case_result_id is not None:
            latest_by_target.setdefault(("case", item.evaluation_case_result_id), item)
        elif item.orchestration_id is not None:
            latest_by_target.setdefault(("orchestration", item.orchestration_id), item)

    reviewed = 0
    reviewed_correct = 0
    false_positive = 0
    false_negative = 0
    for (target_type, target_id), feedback in latest_by_target.items():
        if target_type != "case" or feedback.verdict == "rejected":
            continue
        result = db.get(EvaluationCaseResult, target_id)
        if result is None:
            continue
        effective_decision = feedback.corrected_decision if feedback.verdict == "corrected" else result.actual_decision
        reviewed += 1
        reviewed_correct += int(effective_decision == result.expected_decision)
        false_positive += int(result.expected_decision == "approve" and effective_decision != "approve")
        false_negative += int(result.expected_decision != "approve" and effective_decision == "approve")

    return DecisionFeedbackSummaryResponse(
        total=total,
        accepted=accepted,
        rejected=rejected,
        corrected=corrected,
        acceptance_rate=round(accepted / total, 4) if total else 0.0,
        correction_rate=round(corrected / total, 4) if total else 0.0,
        reviewed_accuracy=round(reviewed_correct / reviewed, 4) if reviewed else 0.0,
        false_positive_rate=round(false_positive / reviewed, 4) if reviewed else 0.0,
        false_negative_rate=round(false_negative / reviewed, 4) if reviewed else 0.0,
        recent=[_to_feedback_read(item) for item in records[:20]],
    )


def create_pilot_measurement(db: Session, payload: PilotMeasurementCreate) -> PilotMeasurementRead:
    record = PilotMeasurement(
        subject=sanitize_for_log(payload.subject, max_chars=120),
        team_subject=sanitize_for_log(payload.team_subject, max_chars=120),
        metric=payload.metric,
        phase=payload.phase,
        value=payload.value,
        unit=payload.unit,
        sample_size=payload.sample_size,
        source=sanitize_for_log(payload.source, max_chars=64) or "observed",
        notes=sanitize_for_log(payload.notes, max_chars=2000),
        measured_at=payload.measured_at or utcnow_naive(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_measurement_read(record)


def get_pilot_comparison(
    db: Session,
    *,
    subject: str | None = None,
    team_subject: str | None = None,
) -> PilotComparisonResponse:
    query = db.query(PilotMeasurement)
    if subject:
        query = query.filter(PilotMeasurement.subject == subject)
    if team_subject:
        query = query.filter(PilotMeasurement.team_subject == team_subject)
    records = query.order_by(PilotMeasurement.measured_at.desc(), PilotMeasurement.id.desc()).all()

    grouped: dict[tuple[str, str], list[PilotMeasurement]] = defaultdict(list)
    for item in records:
        grouped[(item.metric, item.phase)].append(item)

    metrics: list[PilotMetricComparison] = []
    for metric in METRIC_ORDER:
        baseline, baseline_n, baseline_unit = _weighted_measurement(grouped.get((metric, "baseline"), []))
        pilot, pilot_n, pilot_unit = _weighted_measurement(grouped.get((metric, "pilot"), []))
        if baseline is None and pilot is None:
            continue
        unit = pilot_unit or baseline_unit or "minutes"
        absolute_change = round(pilot - baseline, 4) if baseline is not None and pilot is not None else None
        improvement_rate = None
        if baseline is not None and pilot is not None and baseline > 0:
            improvement_rate = round((baseline - pilot) / baseline, 4)
        metrics.append(
            PilotMetricComparison(
                metric=metric,
                unit=unit,
                baseline_value=baseline,
                pilot_value=pilot,
                absolute_change=absolute_change,
                improvement_rate=improvement_rate,
                baseline_sample_size=baseline_n,
                pilot_sample_size=pilot_n,
            )
        )

    complete_metrics = [item for item in metrics if item.baseline_value is not None and item.pilot_value is not None]
    if complete_metrics:
        summary = f"{len(complete_metrics)} measured metric(s) compare baseline with pilot observations."
        source = "measured"
    else:
        summary = "Record both baseline and pilot observations to replace directional ROI assumptions."
        source = "not_configured"
    return PilotComparisonResponse(
        subject=subject,
        team_subject=team_subject,
        source=source,
        metrics=metrics,
        measured_value_summary=summary,
    )


def deterministic_release_gate_decision(release_input: ReleaseGatePrCiInput) -> ReleaseGateDecision:
    combined = " ".join(
        [
            release_input.pr_diff_summary,
            release_input.ci_log_summary,
            release_input.target_environment,
            release_input.change_risk,
        ]
    ).lower()
    if any(marker in combined for marker in ("secret", "credential", "data loss", "rollback failed", "security critical")):
        return "block"
    if any(marker in combined for marker in ("failed", "flaky", "timeout", "timed out", "migration", "production", "prod", "high risk", "owner", "rollback-sensitive")):
        return "needs human review"
    return "approve"


def _to_evaluation_run_read(db: Session, record: EvaluationRun) -> EvaluationRunRead:
    results = (
        db.query(EvaluationCaseResult)
        .filter(EvaluationCaseResult.evaluation_run_id == record.id)
        .order_by(EvaluationCaseResult.id.asc())
        .all()
    )
    return EvaluationRunRead(
        id=record.id,
        dataset_version=record.dataset_version,
        provider=record.provider,
        model=record.model,
        prompt_version=record.prompt_version,
        mode=record.mode,  # type: ignore[arg-type]
        status=record.status,
        case_count=record.case_count,
        correct_count=record.correct_count,
        false_positive_count=record.false_positive_count,
        false_negative_count=record.false_negative_count,
        accuracy=record.accuracy,
        average_latency_ms=record.average_latency_ms,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        estimated_cost_usd=record.estimated_cost_microusd / 1_000_000,
        created_at=record.created_at,
        completed_at=record.completed_at,
        results=[
            EvaluationCaseResultRead(
                id=item.id,
                case_id=item.case_id,
                expected_decision=item.expected_decision,  # type: ignore[arg-type]
                actual_decision=item.actual_decision,  # type: ignore[arg-type]
                is_correct=item.is_correct,
                confidence=item.confidence,
                rationale=item.rationale,
                latency_ms=item.latency_ms,
            )
            for item in results
        ],
    )


def _to_feedback_read(record: DecisionFeedback) -> DecisionFeedbackRead:
    return DecisionFeedbackRead(
        id=record.id,
        evaluation_case_result_id=record.evaluation_case_result_id,
        orchestration_id=record.orchestration_id,
        verdict=record.verdict,
        corrected_decision=record.corrected_decision,
        actor=record.actor,
        note=record.note,
        created_at=record.created_at,
    )


def _to_measurement_read(record: PilotMeasurement) -> PilotMeasurementRead:
    return PilotMeasurementRead(
        id=record.id,
        subject=record.subject,
        team_subject=record.team_subject,
        metric=record.metric,
        phase=record.phase,
        value=record.value,
        unit=record.unit,
        sample_size=record.sample_size,
        source=record.source,
        notes=record.notes,
        measured_at=record.measured_at,
        created_at=record.created_at,
    )


def _weighted_measurement(records: list[PilotMeasurement]) -> tuple[float | None, int, str]:
    if not records:
        return None, 0, ""
    sample_size = sum(max(1, item.sample_size) for item in records)
    weighted = sum(item.value * max(1, item.sample_size) for item in records) / sample_size
    return round(weighted, 4), sample_size, records[0].unit
