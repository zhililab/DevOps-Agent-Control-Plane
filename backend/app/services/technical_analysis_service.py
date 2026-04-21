import json
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.models import TechnicalAnalysis
from app.schemas import (
    TechnicalAnalysisHistoryResponse,
    TechnicalAnalysisInput,
    TechnicalAnalysisOutput,
    TechnicalAnalysisSavedResponse,
)
from app.services.agent_log_service import log_agent_action

logger = logging.getLogger(__name__)


def create_technical_analysis(
    db: Session, payload: TechnicalAnalysisInput
) -> TechnicalAnalysisSavedResponse:
    logger.info(
        "technical_analysis.request_received logs_len=%s errors=%s snippets=%s issue_len=%s",
        len(payload.logs.strip()),
        len(payload.errors),
        len(payload.code_snippets),
        len(payload.issue_description.strip()),
    )
    log_agent_action(
        db,
        task_type="technical_analysis_request",
        input_summary=json.dumps(payload.model_dump(mode="json")),
        output_summary="request accepted",
        status="received",
    )

    generated = _generate_structured_analysis(payload)
    record = TechnicalAnalysis(
        analysis_date=date.today(),
        input_json=json.dumps(_normalized_input(payload).model_dump(mode="json")),
        output_json=json.dumps(generated.model_dump(mode="json")),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info("technical_analysis.persisted analysis_id=%s", record.id)
    log_agent_action(
        db,
        task_type="technical_analysis_persisted",
        input_summary=f"analysis_id={record.id}",
        output_summary=generated.problem_statement,
        status="success",
    )

    return TechnicalAnalysisSavedResponse(
        id=record.id,
        analysis_date=record.analysis_date,
        input=_normalized_input(payload),
        output=generated,
        created_at=record.created_at,
    )


def list_technical_analyses(db: Session) -> TechnicalAnalysisHistoryResponse:
    records = db.query(TechnicalAnalysis).order_by(TechnicalAnalysis.created_at.desc()).all()
    logger.info("technical_analysis.history_requested total=%s", len(records))
    log_agent_action(
        db,
        task_type="technical_analysis_history_requested",
        input_summary="history list",
        output_summary=f"returned {len(records)} analysis item(s)",
        status="success",
    )
    items = [
        TechnicalAnalysisSavedResponse(
            id=record.id,
            analysis_date=record.analysis_date,
            input=TechnicalAnalysisInput.model_validate(json.loads(record.input_json or "{}")),
            output=TechnicalAnalysisOutput.model_validate(json.loads(record.output_json or "{}")),
            created_at=record.created_at,
        )
        for record in records
    ]
    return TechnicalAnalysisHistoryResponse(items=items)


def _generate_structured_analysis(payload: TechnicalAnalysisInput) -> TechnicalAnalysisOutput:
    normalized = _normalized_input(payload)
    logs = normalized.logs
    errors = normalized.errors
    snippets = normalized.code_snippets
    issue_description = normalized.issue_description

    primary_signal = _primary_signal(issue_description, errors, logs, snippets)
    problem_statement = f"Observed technical issue: {primary_signal}"

    likely_causes = _likely_causes(errors, logs, snippets)
    validation_steps = _validation_steps(primary_signal, errors, logs, snippets)
    fix_options = _fix_options(likely_causes)
    risks = _risks_from_causes(likely_causes)
    follow_up_tasks = _follow_up_tasks(primary_signal, fix_options)

    return TechnicalAnalysisOutput(
        problem_statement=problem_statement,
        likely_causes=likely_causes,
        validation_steps=validation_steps,
        fix_options=fix_options,
        risks=risks,
        follow_up_tasks=follow_up_tasks,
    )


def _normalized_input(payload: TechnicalAnalysisInput) -> TechnicalAnalysisInput:
    return TechnicalAnalysisInput(
        logs=payload.logs.strip(),
        errors=_normalize_lines(payload.errors),
        code_snippets=_normalize_lines(payload.code_snippets),
        issue_description=payload.issue_description.strip(),
    )


def _normalize_lines(items: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in items:
        clean = item.strip()
        if clean and clean not in normalized:
            normalized.append(clean)
    return normalized


def _primary_signal(
    issue_description: str, errors: list[str], logs: str, snippets: list[str]
) -> str:
    if issue_description:
        return issue_description
    if errors:
        return errors[0]
    if logs:
        return logs.splitlines()[0].strip()
    if snippets:
        return f"Code path snippet starts with: {snippets[0][:120]}"
    return "Unknown issue signal"


def _likely_causes(errors: list[str], logs: str, snippets: list[str]) -> list[str]:
    combined = " ".join(errors + [logs]).lower()
    causes: list[str] = []

    if "timeout" in combined:
        causes.append("Dependency response exceeded timeout budget under current retry/backoff settings.")
    if "permission" in combined or "denied" in combined or "forbidden" in combined:
        causes.append("Credential, token scope, or IAM policy does not permit the failing operation.")
    if "connection refused" in combined or "connection reset" in combined or "unreachable" in combined:
        causes.append("Target service endpoint is unavailable or network routing is failing.")
    if "out of memory" in combined or "oom" in combined:
        causes.append("Runtime memory pressure is triggering process kill or degraded execution.")
    if "nullpointer" in combined or "noneType" in combined:
        causes.append("Missing null/None guard in the failing code path.")
    if not causes and snippets:
        causes.append("Recent code path likely lacks boundary checks or defensive error handling.")
    if not causes:
        causes.append("Recent config/deploy drift introduced mismatch between expected and runtime behavior.")

    return causes[:4]


def _validation_steps(
    primary_signal: str, errors: list[str], logs: str, snippets: list[str]
) -> list[str]:
    steps = [
        f"Reproduce once with stable input and confirm the same symptom: '{primary_signal[:140]}'.",
    ]
    if errors:
        steps.append(f"Filter logs for error signature: '{errors[0][:120]}' and capture first occurrence timestamp.")
    elif logs:
        steps.append("Extract 3-5 log lines before/after failure point to confirm sequence and dependency involved.")
    else:
        steps.append("Capture runtime logs around failure window to avoid hypothesis based on incomplete evidence.")

    if snippets:
        steps.append("Execute targeted test around provided code snippet and assert expected error-handling behavior.")
    else:
        steps.append("Compare latest deploy/config diff with last known healthy version to isolate behavior change.")

    steps.append("After fix attempt, rerun the same reproduction and verify metrics/logs return to baseline.")
    return steps[:5]


def _fix_options(likely_causes: list[str]) -> list[str]:
    options: list[str] = []
    for cause in likely_causes:
        if "timeout" in cause.lower():
            options.append("Increase client timeout modestly and add bounded retries with jitter while tracking p95 latency.")
        elif "credential" in cause.lower() or "iam" in cause.lower():
            options.append("Align service account/role permissions with required API actions and rotate stale tokens.")
        elif "endpoint" in cause.lower() or "network" in cause.lower():
            options.append("Validate service discovery and network policy, then fail over to a healthy endpoint if available.")
        elif "memory" in cause.lower():
            options.append("Raise memory limit for workload and reduce peak allocation in heavy code path.")
        elif "null" in cause.lower() or "none" in cause.lower():
            options.append("Add null guards with explicit fallback behavior and extend tests for missing data cases.")
        else:
            options.append("Rollback the recent risky change first, then apply a narrow fix with monitoring enabled.")

    if len(options) < 2:
        options.append("Ship fix behind a feature flag to limit blast radius during verification.")
    return options[:4]


def _risks_from_causes(likely_causes: list[str]) -> list[str]:
    risks: list[str] = []
    for cause in likely_causes:
        if "timeout" in cause.lower():
            risks.append("Masking root latency by only increasing timeout can worsen queueing under peak load.")
        elif "credential" in cause.lower() or "iam" in cause.lower():
            risks.append("Over-broad permission updates can create security exposure.")
        elif "network" in cause.lower() or "endpoint" in cause.lower():
            risks.append("Endpoint failover without data consistency checks may introduce stale reads/writes.")
        elif "memory" in cause.lower():
            risks.append("Raising memory limits alone may hide memory leak regressions.")
        else:
            risks.append("Quick rollback may impact unrelated features depending on the same deployment bundle.")

    if not risks:
        risks.append("Insufficient reproduction evidence can lead to fixing symptoms instead of root cause.")
    return risks[:4]


def _follow_up_tasks(primary_signal: str, fix_options: list[str]) -> list[str]:
    tasks = [
        f"Document incident note with symptom and timeline: '{primary_signal[:120]}'.",
        "Add one automated regression test covering this failure mode.",
        f"Create implementation task for selected fix option: '{fix_options[0][:120]}'.",
        "Update runbook with detection query and first-response checklist for this issue class.",
    ]
    return tasks
