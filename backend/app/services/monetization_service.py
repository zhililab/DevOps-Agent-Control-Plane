from __future__ import annotations

import json
from calendar import monthrange
from datetime import datetime, time, timedelta
from typing import Literal

from sqlalchemy.orm import Session

from app.models import (
    AgentRunLog,
    MonetizationEvent,
    MonetizationEventKind,
    SubscriptionProfile,
    SubscriptionStatus,
    SubscriptionTier,
    UsageCounter,
    UsageMetric,
    WorkflowOrchestration,
    WorkflowTemplate,
)
from app.schemas import (
    CommercialMetricsAnomalyHint,
    CommercialMetricsBillableWorkUnits,
    CommercialMetricsEventSummary,
    CommercialMetricsPlanUsage,
    CommercialMetricsPolicyBlocks,
    CommercialMetricsResponse,
    CommercialMetricsRoiSummary,
    CommercialMetricsRoiTemplateBreakdown,
    CommercialMetricsSubscriptionSummary,
    CommercialMetricsTopTemplate,
    CommercialMetricsTrendPoint,
    CommercialMetricsUsageSummary,
    MonetizationEventRead,
    PilotCloseoutReportResponse,
    PilotPowerUpgradeEvidence,
    PilotReadinessReportResponse,
    PilotScenarioCompletionRead,
    PilotScenarioCompletionSummary,
    MonetizationTier,
    SubscriptionLifecycleResponse,
    SubscriptionProfileRead,
    UsageCounterRead,
    WorkflowTemplatePolicy,
)
from app.services.entitlement_service import subject_id_for_entitlement_user
from app.services.history_ledger import summarize_orchestration_histories
from app.services.pilot_scenarios import list_pilot_scenarios
from app.services.roi_service import compute_workflow_roi_evidence, decision_from_summary_text
from app.services.workflow_checkpoints import summarize_checkpoint_counts
from app.time_utils import business_date_from_utc, utcnow_naive


TIER_ENTITLEMENTS: dict[str, dict[str, object]] = {
    "free": {
        "workflow_runs": 25,
        "queued_runs": 25,
        "max_enabled_steps": 1,
        "policy_templates": False,
        "approval_gates": False,
    },
    "pro": {
        "workflow_runs": 300,
        "queued_runs": 300,
        "max_enabled_steps": 3,
        "policy_templates": True,
        "approval_gates": False,
    },
    "power": {
        "workflow_runs": 2000,
        "queued_runs": 2000,
        "max_enabled_steps": 3,
        "policy_templates": True,
        "approval_gates": True,
    },
}

POLICY_BLOCK_LOG_TYPES = {
    "monetization.approval_required_blocked",
    "monetization.template_policy_upgrade_required",
    "monetization.capability_blocked_upgrade_required",
    "monetization.quota_exceeded",
}
VALID_TEMPLATE_RISKS = {"low", "medium", "high", "critical"}


def usage_metric_for_endpoint(endpoint: str) -> UsageMetric | None:
    if endpoint == "/api/orchestrations/run":
        return UsageMetric.workflow_runs
    if endpoint == "/api/orchestrations/queue/run":
        return UsageMetric.queued_runs
    return None


def record_plan_usage(
    db: Session,
    *,
    subject: str | None,
    metric: UsageMetric | None,
    endpoint: str,
    tier: str,
    subject_id: str,
    quantity: int = 1,
) -> UsageCounterRead | None:
    if not subject or metric is None or quantity <= 0:
        return None

    now = utcnow_naive()
    profile = _get_active_profile_for_usage(db, subject=subject, now=now)
    if profile is None:
        return None

    entitlements = _safe_json_dict(profile.entitlements_json) or _entitlements_for_tier(profile.tier.value)
    counters = _upsert_current_period_counters(db, profile=profile, entitlements=entitlements, now=now)
    counter = next((item for item in counters if item.metric == metric), None)
    if counter is None:
        return None

    counter.used = max(0, int(counter.used)) + quantity
    counter.updated_at = now
    event = MonetizationEvent(
        subscription_profile_id=profile.id,
        usage_counter_id=counter.id,
        event_kind=MonetizationEventKind.usage_recorded,
        event_json=json.dumps(
            {
                "version": 1,
                "action": "usage_recorded",
                "subject": profile.subject,
                "metric": metric.value,
                "endpoint": endpoint,
                "tier": tier,
                "subject_id": subject_id,
                "quantity": quantity,
                "used": counter.used,
                "limit": counter.limit,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        created_at=now,
    )
    db.add(event)
    db.commit()
    db.refresh(counter)
    return UsageCounterRead.model_validate(counter)


def get_plan_usage_quota(
    db: Session,
    *,
    subject: str | None,
    metric: UsageMetric | None,
) -> dict[str, object] | None:
    if not subject or metric is None:
        return None

    now = utcnow_naive()
    profile = _get_active_profile_for_usage(db, subject=subject, now=now)
    if profile is None:
        return None

    entitlements = _safe_json_dict(profile.entitlements_json) or _entitlements_for_tier(profile.tier.value)
    counters = _upsert_current_period_counters(db, profile=profile, entitlements=entitlements, now=now)
    counter = next((item for item in counters if item.metric == metric), None)
    if counter is None:
        return None
    return {
        "used": int(counter.used),
        "limit": int(counter.limit),
        "period_start": counter.period_start.isoformat(),
        "period_end": counter.period_end.isoformat(),
        "metric": metric.value,
        "subject": profile.subject,
    }


def backfill_current_period_usage_counters(db: Session, *, subject: str | None = None) -> int:
    normalized_subject = subject.strip() if subject and subject.strip() else None
    profiles = _latest_profiles(db, subject=normalized_subject)
    now = utcnow_naive()
    changed = 0

    for profile in profiles:
        if _get_active_profile_for_usage(db, subject=profile.subject, now=now) is None:
            continue

        entitlements = _safe_json_dict(profile.entitlements_json) or _entitlements_for_tier(profile.tier.value)
        counters = _upsert_current_period_counters(db, profile=profile, entitlements=entitlements, now=now)
        for counter in counters:
            endpoint = _endpoint_for_usage_metric(counter.metric)
            counted_logs = _count_current_period_usage_logs(
                db,
                subject=profile.subject,
                endpoint=endpoint,
                period_start=counter.period_start,
                period_end=counter.period_end,
            )
            if counter.used < counted_logs:
                counter.used = counted_logs
                counter.updated_at = now
                changed += 1

    db.commit()
    return changed


def get_subscription_profile(db: Session, *, subject: str) -> SubscriptionProfileRead | None:
    profile = (
        db.query(SubscriptionProfile)
        .filter(SubscriptionProfile.subject == subject)
        .order_by(SubscriptionProfile.updated_at.desc(), SubscriptionProfile.id.desc())
        .first()
    )
    if profile is None:
        return None
    return _to_subscription_profile_read(profile)


def list_usage_counters(db: Session, *, subject: str) -> list[UsageCounterRead]:
    backfill_current_period_usage_counters(db, subject=subject)
    profile = (
        db.query(SubscriptionProfile)
        .filter(SubscriptionProfile.subject == subject)
        .order_by(SubscriptionProfile.updated_at.desc(), SubscriptionProfile.id.desc())
        .first()
    )
    if profile is None:
        return []

    counters = (
        db.query(UsageCounter)
        .filter(UsageCounter.subscription_profile_id == profile.id)
        .order_by(
            UsageCounter.metric.asc(),
            UsageCounter.period_start.desc(),
            UsageCounter.period_end.desc(),
            UsageCounter.id.desc(),
        )
        .all()
    )
    return [UsageCounterRead.model_validate(counter) for counter in counters]


def list_monetization_events(db: Session, *, limit: int, subject: str | None = None) -> list[MonetizationEventRead]:
    query = db.query(MonetizationEvent)
    if subject:
        query = query.join(SubscriptionProfile, MonetizationEvent.subscription_profile_id == SubscriptionProfile.id).filter(
            SubscriptionProfile.subject == subject
        )

    events = query.order_by(MonetizationEvent.created_at.desc(), MonetizationEvent.id.desc()).limit(limit).all()
    return [_to_monetization_event_read(event) for event in events]


def get_commercial_metrics(
    db: Session,
    *,
    days: int = 7,
    subject: str | None = None,
) -> CommercialMetricsResponse:
    period_days = 30 if int(days) == 30 else 7
    generated_at = utcnow_naive()
    window_start = generated_at - timedelta(days=period_days)
    normalized_subject = subject.strip() if subject and subject.strip() else None
    backfill_current_period_usage_counters(db, subject=normalized_subject)

    latest_profiles = _latest_profiles(db, subject=normalized_subject)
    profile_ids = [profile.id for profile in latest_profiles]
    subscription_summary = _build_subscription_summary(latest_profiles)

    usage_logs = _list_monetization_logs(
        db,
        window_start=window_start,
        subject=normalized_subject,
        task_types={"monetization.usage_recorded"},
    )
    workflow_run_logs = [
        log
        for log in usage_logs
        if _log_payload(log).get("endpoint") == "/api/orchestrations/run"
        and isinstance(_log_payload(log).get("orchestration_id"), int)
    ]
    queued_run_logs = [
        log
        for log in usage_logs
        if _log_payload(log).get("endpoint") == "/api/orchestrations/queue/run"
        and isinstance(_log_payload(log).get("queue_job_id"), int)
    ]
    counters = _usage_counters_for_profiles(db, profile_ids)
    plan_usage = _build_plan_usage(counters)
    usage_summary = CommercialMetricsUsageSummary(
        workflow_runs_used=len(workflow_run_logs),
        workflow_runs_limit=_counter_limit(counters, UsageMetric.workflow_runs),
        queued_runs_used=len(queued_run_logs),
        queued_runs_limit=_counter_limit(counters, UsageMetric.queued_runs),
        usage_subjects=len(
            {
                subject_id
                for subject_id in (_log_payload(log).get("subject_id") for log in usage_logs)
                if isinstance(subject_id, str) and subject_id
            }
        ),
    )

    subject_orchestration_ids = {
        orchestration_id
        for orchestration_id in (_log_payload(log).get("orchestration_id") for log in workflow_run_logs)
        if isinstance(orchestration_id, int)
    }
    orchestration_records = _list_metric_orchestrations(
        db,
        window_start=window_start,
        subject=normalized_subject,
        subject_orchestration_ids=subject_orchestration_ids,
    )
    templates_by_id = _templates_by_id_for_orchestrations(db, orchestration_records)
    checkpoint_counts = summarize_checkpoint_counts(db, [record.id for record in orchestration_records])
    top_templates = _build_top_templates(orchestration_records, templates_by_id)
    roi_summary = _build_roi_summary(orchestration_records, templates_by_id, checkpoint_counts)
    billable_total = sum(item.billable_work_units for item in top_templates)
    audited_workflows = len(
        [record for record in orchestration_records if record.status in {"success", "partial_success"}]
    )

    block_logs = _list_monetization_logs(
        db,
        window_start=window_start,
        subject=normalized_subject,
        task_types=POLICY_BLOCK_LOG_TYPES,
    )
    policy_blocks = CommercialMetricsPolicyBlocks(
        approval_required=len([log for log in block_logs if log.task_type == "monetization.approval_required_blocked"]),
        upgrade_required=len(
            [
                log
                for log in block_logs
                if log.task_type
                in {
                    "monetization.template_policy_upgrade_required",
                    "monetization.capability_blocked_upgrade_required",
                }
            ]
        ),
        quota_exceeded=len([log for log in block_logs if log.task_type == "monetization.quota_exceeded"]),
        total=len(block_logs),
    )

    commercial_events = _build_commercial_events(
        db,
        window_start=window_start,
        profile_ids=profile_ids,
        subject=normalized_subject,
    )
    trend = _build_commercial_trend(
        generated_at=generated_at,
        period_days=period_days,
        orchestration_records=orchestration_records,
        templates_by_id=templates_by_id,
        block_logs=block_logs,
    )
    anomaly_hints = _build_commercial_anomaly_hints(
        subscription_summary=subscription_summary,
        usage_summary=usage_summary,
        policy_blocks=policy_blocks,
        billable_work_units=billable_total,
    )

    return CommercialMetricsResponse(
        window_days=period_days,
        generated_at=generated_at,
        subject=normalized_subject,
        subscription_summary=subscription_summary,
        usage_summary=usage_summary,
        plan_usage=plan_usage,
        commercial_events=commercial_events,
        policy_blocks=policy_blocks,
        billable_work_units=CommercialMetricsBillableWorkUnits(
            total=billable_total,
            audited_workflows=audited_workflows,
            average_per_run=round(billable_total / len(orchestration_records), 2)
            if orchestration_records
            else 0.0,
        ),
        roi_summary=roi_summary,
        top_templates=top_templates,
        trend=trend,
        anomaly_hints=anomaly_hints,
    )


def get_pilot_readiness_report(
    db: Session,
    *,
    days: int = 7,
    subject: str | None = None,
    team_subject: str | None = None,
) -> PilotReadinessReportResponse:
    period_days = 30 if int(days) == 30 else 7
    generated_at = utcnow_naive()
    window_start = generated_at - timedelta(days=period_days)
    normalized_subject = subject.strip() if subject and subject.strip() else None
    normalized_team = team_subject.strip() if team_subject and team_subject.strip() else None

    records = _list_pilot_report_records(
        db,
        window_start=window_start,
        subject=normalized_subject,
        team_subject=normalized_team,
    )
    completed_records = [record for record in records if record.status in {"success", "partial_success"}]
    orchestration_ids = [record.id for record in completed_records]
    templates_by_id = _templates_by_id_for_orchestrations(db, completed_records)
    checkpoint_counts = summarize_checkpoint_counts(db, orchestration_ids)
    ledger_summaries = summarize_orchestration_histories(db, orchestration_ids)
    roi_summary = _build_roi_summary(completed_records, templates_by_id, checkpoint_counts)
    scenario_statuses = _build_pilot_scenario_statuses(
        completed_records,
        checkpoint_counts=checkpoint_counts,
        ledger_summaries=ledger_summaries,
    )

    evidence_exportable_runs = len(
        [
            record
            for record in completed_records
            if _safe_json_dict(record.result_json).get("conclusion") or checkpoint_counts.get(record.id, 0) > 0
        ]
    )
    ledger_valid_runs = len(
        [
            record
            for record in completed_records
            if ledger_summaries.get(record.id, {}).get("integrity_status") == "valid"
            and int(ledger_summaries.get(record.id, {}).get("event_count", 0) or 0) > 0
        ]
    )
    checkpointed_runs = len([record for record in completed_records if checkpoint_counts.get(record.id, 0) > 0])

    approval_required_runs = 0
    blocked_or_needs_review_runs = 0
    missing_metadata_runs = 0
    metadata_fields_present = 0
    metadata_fields_total = len(completed_records) * 4
    for record in completed_records:
        policy = _policy_for_record(record, templates_by_id)
        if policy.approval_required:
            approval_required_runs += 1
        decision = decision_from_summary_text(str(_summary_from_result_json(record.result_json)["conclusion"]))
        if decision in {"block", "needs human review"}:
            blocked_or_needs_review_runs += 1

        fields = [record.team_subject, record.requested_by, record.approval_actor, record.approval_note]
        present_count = len([value for value in fields if isinstance(value, str) and value.strip()])
        metadata_fields_present += present_count
        if present_count < len(fields):
            missing_metadata_runs += 1

    metadata_completeness = (
        round(metadata_fields_present / metadata_fields_total, 2) if metadata_fields_total > 0 else 0.0
    )
    completed_scenarios = len([item for item in scenario_statuses if item.status == "completed"])
    scenario_completion = _build_pilot_scenario_completion_summary(
        scenario_statuses,
        evidence_exportable_runs=evidence_exportable_runs,
        ledger_valid_runs=ledger_valid_runs,
        checkpointed_runs=checkpointed_runs,
        metadata_completeness=metadata_completeness,
    )
    status = _pilot_readiness_status(
        runs_completed=len(completed_records),
        completed_scenarios=completed_scenarios,
        evidence_exportable_runs=evidence_exportable_runs,
        ledger_valid_runs=ledger_valid_runs,
        checkpointed_runs=checkpointed_runs,
        metadata_completeness=metadata_completeness,
        ready_for_buyer_review=scenario_completion.ready_for_buyer_review,
    )
    power_upgrade_evidence = _build_power_upgrade_evidence(
        approval_required_runs=approval_required_runs,
        blocked_or_needs_review_runs=blocked_or_needs_review_runs,
        evidence_exportable_runs=evidence_exportable_runs,
        ledger_valid_runs=ledger_valid_runs,
        roi_summary=roi_summary,
        scenario_statuses=scenario_statuses,
    )

    return PilotReadinessReportResponse(
        window_days=period_days,
        generated_at=generated_at,
        subject=normalized_subject,
        team_subject=normalized_team,
        status=status,
        runs_completed=len(completed_records),
        evidence_exportable_runs=evidence_exportable_runs,
        ledger_valid_runs=ledger_valid_runs,
        checkpointed_runs=checkpointed_runs,
        approval_required_runs=approval_required_runs,
        blocked_or_needs_review_runs=blocked_or_needs_review_runs,
        estimated_value_usd=roi_summary.estimated_customer_value_usd,
        review_time_saved_minutes=roi_summary.review_time_saved_minutes,
        audit_time_saved_minutes=roi_summary.audit_time_saved_minutes,
        metadata_completeness=metadata_completeness,
        missing_metadata_runs=missing_metadata_runs,
        scenario_statuses=scenario_statuses,
        scenario_completion=scenario_completion,
        power_upgrade_evidence=power_upgrade_evidence,
        success_criteria=[
            "5/5 pilot scenarios completed",
            "5+ evidence-exportable release-gate runs",
            "Ledger valid on completed runs",
            "Checkpoint snapshots present",
            "80%+ team/requester/approver metadata completeness",
        ],
        recommendations=_pilot_readiness_recommendations(
            runs_completed=len(completed_records),
            completed_scenarios=completed_scenarios,
            evidence_exportable_runs=evidence_exportable_runs,
            ledger_valid_runs=ledger_valid_runs,
            checkpointed_runs=checkpointed_runs,
            metadata_completeness=metadata_completeness,
            scenario_completion=scenario_completion,
        ),
    )


def get_pilot_closeout_report(
    db: Session,
    *,
    days: int = 7,
    subject: str | None = None,
    team_subject: str | None = None,
) -> PilotCloseoutReportResponse:
    report = get_pilot_readiness_report(db, days=days, subject=subject, team_subject=team_subject)
    markdown = _build_pilot_closeout_markdown(report)
    return PilotCloseoutReportResponse(
        window_days=report.window_days,
        generated_at=utcnow_naive(),
        subject=report.subject,
        team_subject=report.team_subject,
        status=report.status,
        markdown=markdown,
        data=report.model_dump(mode="json"),
    )


def start_manual_checkout(
    db: Session,
    *,
    subject: str,
    target_tier: MonetizationTier,
    billing_provider: str = "manual",
) -> SubscriptionLifecycleResponse:
    now = utcnow_naive()
    profile = _get_latest_profile_model(db, subject=subject)
    previous_tier = profile.tier.value if profile is not None else None
    action = "checkout_completed" if profile is None else "tier_changed"

    if profile is None:
        profile = SubscriptionProfile(
            subject=subject,
            tier=SubscriptionTier(target_tier),
            status=SubscriptionStatus.active,
            billing_provider=billing_provider,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=False,
            entitlements_json="{}",
            created_at=now,
            updated_at=now,
        )
        db.add(profile)
        db.flush()
    else:
        profile.tier = SubscriptionTier(target_tier)
        profile.status = SubscriptionStatus.active
        profile.billing_provider = billing_provider
        profile.cancel_at_period_end = False
        profile.current_period_start = profile.current_period_start or now
        profile.current_period_end = profile.current_period_end or (now + timedelta(days=30))
        profile.updated_at = now

    entitlements = _entitlements_for_tier(target_tier)
    profile.entitlements_json = json.dumps(entitlements, sort_keys=True, separators=(",", ":"))
    counters = _upsert_current_period_counters(db, profile=profile, entitlements=entitlements, now=now)
    event = _append_subscription_event(
        db,
        profile=profile,
        action=action,
        now=now,
        payload={
            "action": action,
            "provider": billing_provider,
            "subject": subject,
            "previous_tier": previous_tier,
            "new_tier": target_tier,
            "status": profile.status.value,
            "cancel_at_period_end": profile.cancel_at_period_end,
        },
    )
    db.commit()
    db.refresh(profile)
    for counter in counters:
        db.refresh(counter)
    db.refresh(event)
    return SubscriptionLifecycleResponse(
        profile=_to_subscription_profile_read(profile),
        counters=[UsageCounterRead.model_validate(counter) for counter in counters],
        event=_to_monetization_event_read(event),
    )


def cancel_subscription(db: Session, *, subject: str) -> SubscriptionLifecycleResponse:
    profile = _get_latest_profile_model(db, subject=subject)
    now = utcnow_naive()
    if profile is None:
        profile = SubscriptionProfile(
            subject=subject,
            tier=SubscriptionTier.free,
            status=SubscriptionStatus.inactive,
            billing_provider="manual",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=True,
            entitlements_json=json.dumps(_entitlements_for_tier("free"), sort_keys=True, separators=(",", ":")),
            created_at=now,
            updated_at=now,
        )
        db.add(profile)
        db.flush()
    else:
        profile.cancel_at_period_end = True
        profile.updated_at = now

    counters = _upsert_current_period_counters(
        db,
        profile=profile,
        entitlements=_safe_json_dict(profile.entitlements_json) or _entitlements_for_tier(profile.tier.value),
        now=now,
    )
    event = _append_subscription_event(
        db,
        profile=profile,
        action="cancel_requested",
        now=now,
        payload={
            "action": "cancel_requested",
            "provider": profile.billing_provider,
            "subject": subject,
            "tier": profile.tier.value,
            "status": profile.status.value,
            "cancel_at_period_end": profile.cancel_at_period_end,
        },
    )
    db.commit()
    db.refresh(profile)
    for counter in counters:
        db.refresh(counter)
    db.refresh(event)
    return SubscriptionLifecycleResponse(
        profile=_to_subscription_profile_read(profile),
        counters=[UsageCounterRead.model_validate(counter) for counter in counters],
        event=_to_monetization_event_read(event),
    )


def reactivate_subscription(db: Session, *, subject: str) -> SubscriptionLifecycleResponse:
    profile = _get_latest_profile_model(db, subject=subject)
    now = utcnow_naive()
    if profile is None:
        return start_manual_checkout(db, subject=subject, target_tier="free", billing_provider="manual")

    profile.cancel_at_period_end = False
    if profile.status == SubscriptionStatus.canceled:
        profile.status = SubscriptionStatus.active
    profile.updated_at = now
    counters = _upsert_current_period_counters(
        db,
        profile=profile,
        entitlements=_safe_json_dict(profile.entitlements_json) or _entitlements_for_tier(profile.tier.value),
        now=now,
    )
    event = _append_subscription_event(
        db,
        profile=profile,
        action="reactivated",
        now=now,
        payload={
            "action": "reactivated",
            "provider": profile.billing_provider,
            "subject": subject,
            "tier": profile.tier.value,
            "status": profile.status.value,
            "cancel_at_period_end": profile.cancel_at_period_end,
        },
    )
    db.commit()
    db.refresh(profile)
    for counter in counters:
        db.refresh(counter)
    db.refresh(event)
    return SubscriptionLifecycleResponse(
        profile=_to_subscription_profile_read(profile),
        counters=[UsageCounterRead.model_validate(counter) for counter in counters],
        event=_to_monetization_event_read(event),
    )


def _pilot_readiness_status(
    *,
    runs_completed: int,
    completed_scenarios: int,
    evidence_exportable_runs: int,
    ledger_valid_runs: int,
    checkpointed_runs: int,
    metadata_completeness: float,
    ready_for_buyer_review: bool = False,
) -> str:
    if metadata_completeness < 0.8 and runs_completed > 0:
        return "needs approval metadata"
    if ready_for_buyer_review and completed_scenarios >= 5 and runs_completed >= 5:
        return "ready"
    return "needs evidence"


def _pilot_readiness_recommendations(
    *,
    runs_completed: int,
    completed_scenarios: int,
    evidence_exportable_runs: int,
    ledger_valid_runs: int,
    checkpointed_runs: int,
    metadata_completeness: float,
    scenario_completion: PilotScenarioCompletionSummary | None = None,
) -> list[str]:
    recommendations: list[str] = []
    next_scenario_id = scenario_completion.next_scenario_id if scenario_completion else None
    if next_scenario_id:
        next_scenario = next((item for item in list_pilot_scenarios().items if item.id == next_scenario_id), None)
        recommendations.append(f"Run next guided scenario: {next_scenario.name if next_scenario else next_scenario_id}.")
    if completed_scenarios < 5:
        recommendations.append(f"Complete the full five-scenario pilot pack ({completed_scenarios}/5 completed).")
    if runs_completed < 5:
        recommendations.append("Run the five scenario pack gates before buyer review.")
    if evidence_exportable_runs < runs_completed or evidence_exportable_runs < 5:
        recommendations.append("Export evidence for completed scenario runs.")
    if ledger_valid_runs < runs_completed or ledger_valid_runs < 5:
        recommendations.append("Verify ledger integrity for completed runs.")
    if checkpointed_runs < runs_completed or checkpointed_runs < 5:
        recommendations.append("Confirm checkpoint snapshots are present on each run.")
    if metadata_completeness < 0.8:
        recommendations.append("Fill team, requester, approver, and approval note metadata.")
    if not recommendations:
        recommendations.append("Pilot package is ready for buyer replay.")
    return recommendations


def _list_pilot_report_records(
    db: Session,
    *,
    window_start: datetime,
    subject: str | None,
    team_subject: str | None,
) -> list[WorkflowOrchestration]:
    usage_logs = _list_monetization_logs(
        db,
        window_start=window_start,
        subject=subject,
        task_types={"monetization.usage_recorded"},
    )
    subject_orchestration_ids = {
        orchestration_id
        for orchestration_id in (_log_payload(log).get("orchestration_id") for log in usage_logs)
        if isinstance(orchestration_id, int)
    }

    query = db.query(WorkflowOrchestration).filter(WorkflowOrchestration.created_at >= window_start)
    if subject:
        if not subject_orchestration_ids:
            return []
        query = query.filter(WorkflowOrchestration.id.in_(subject_orchestration_ids))
    if team_subject:
        query = query.filter(WorkflowOrchestration.team_subject == team_subject)
    return query.order_by(WorkflowOrchestration.created_at.desc(), WorkflowOrchestration.id.desc()).all()


def _build_pilot_scenario_statuses(
    records: list[WorkflowOrchestration],
    *,
    checkpoint_counts: dict[int, int],
    ledger_summaries: dict[int, dict[str, object]],
) -> list[PilotScenarioCompletionRead]:
    scenarios = list_pilot_scenarios().items
    records_by_scenario: dict[str, list[WorkflowOrchestration]] = {scenario.id: [] for scenario in scenarios}
    for record in records:
        scenario_id = _pilot_scenario_id_from_request_json(record.request_json)
        if scenario_id in records_by_scenario:
            records_by_scenario[scenario_id].append(record)

    statuses: list[PilotScenarioCompletionRead] = []
    for scenario in scenarios:
        scenario_records = records_by_scenario.get(scenario.id, [])
        evidence_exportable = len(
            [
                record
                for record in scenario_records
                if _safe_json_dict(record.result_json).get("conclusion") or checkpoint_counts.get(record.id, 0) > 0
            ]
        )
        ledger_valid = len(
            [
                record
                for record in scenario_records
                if ledger_summaries.get(record.id, {}).get("integrity_status") == "valid"
                and int(ledger_summaries.get(record.id, {}).get("event_count", 0) or 0) > 0
            ]
        )
        checkpointed = len([record for record in scenario_records if checkpoint_counts.get(record.id, 0) > 0])
        metadata_complete = any(_run_has_buyer_metadata(record) for record in scenario_records)
        status: Literal["missing", "needs evidence", "completed"] = "missing"
        if scenario_records:
            status = "completed" if evidence_exportable and ledger_valid and checkpointed and metadata_complete else "needs evidence"
        latest_id = scenario_records[0].id if scenario_records else None
        statuses.append(
            PilotScenarioCompletionRead(
                id=scenario.id,
                name=scenario.name,
                status=status,
                expected_gate_behavior=scenario.expected_gate_behavior,
                required_tier=scenario.required_tier,
                completed_runs=len(scenario_records),
                evidence_exportable_runs=evidence_exportable,
                ledger_valid_runs=ledger_valid,
                checkpointed_runs=checkpointed,
                approval_metadata_complete=metadata_complete,
                latest_orchestration_id=latest_id,
            )
        )
    return statuses


def _build_pilot_scenario_completion_summary(
    scenario_statuses: list[PilotScenarioCompletionRead],
    *,
    evidence_exportable_runs: int,
    ledger_valid_runs: int,
    checkpointed_runs: int,
    metadata_completeness: float,
) -> PilotScenarioCompletionSummary:
    total = len(scenario_statuses)
    completed = len([item for item in scenario_statuses if item.status == "completed"])
    needs_evidence = len([item for item in scenario_statuses if item.status == "needs evidence"])
    missing = len([item for item in scenario_statuses if item.status == "missing"])
    next_scenario = next((item for item in scenario_statuses if item.status == "missing"), None)
    if next_scenario is None:
        next_scenario = next((item for item in scenario_statuses if item.status == "needs evidence"), None)

    ready_for_buyer_review = (
        total > 0
        and completed == total
        and needs_evidence == 0
        and missing == 0
        and evidence_exportable_runs >= total
        and ledger_valid_runs >= total
        and checkpointed_runs >= total
        and metadata_completeness >= 0.8
    )
    return PilotScenarioCompletionSummary(
        total=total,
        completed=completed,
        needs_evidence=needs_evidence,
        missing=missing,
        next_scenario_id=next_scenario.id if next_scenario else None,
        ready_for_buyer_review=ready_for_buyer_review,
    )


def _build_power_upgrade_evidence(
    *,
    approval_required_runs: int,
    blocked_or_needs_review_runs: int,
    evidence_exportable_runs: int,
    ledger_valid_runs: int,
    roi_summary: CommercialMetricsRoiSummary,
    scenario_statuses: list[PilotScenarioCompletionRead],
) -> PilotPowerUpgradeEvidence:
    power_required_runs = len([item for item in scenario_statuses if item.required_tier == "power" and item.completed_runs > 0])
    review_audit_minutes = roi_summary.review_time_saved_minutes + roi_summary.audit_time_saved_minutes
    if power_required_runs or approval_required_runs or blocked_or_needs_review_runs:
        recommendation = (
            "Power is the recommended pilot plan because the scenario pack uses approval gates, "
            "ledger-backed evidence, and blocked-risk reporting."
        )
    else:
        recommendation = "Run the Power-gated scenario pack to produce upgrade evidence."
    return PilotPowerUpgradeEvidence(
        power_required_runs=power_required_runs,
        approval_required_runs=approval_required_runs,
        blocked_or_needs_review_runs=blocked_or_needs_review_runs,
        evidence_exportable_runs=evidence_exportable_runs,
        ledger_valid_runs=ledger_valid_runs,
        estimated_value_usd=roi_summary.estimated_customer_value_usd,
        review_audit_time_saved_minutes=review_audit_minutes,
        recommendation=recommendation,
    )


def _run_has_buyer_metadata(record: WorkflowOrchestration) -> bool:
    return all(
        isinstance(value, str) and value.strip()
        for value in [record.team_subject, record.requested_by, record.approval_actor, record.approval_note]
    )


def _pilot_scenario_id_from_request_json(value: str) -> str | None:
    payload = _safe_json_dict(value)
    scenario_id = payload.get("pilot_scenario_id")
    if isinstance(scenario_id, str) and scenario_id.strip():
        return scenario_id.strip()[:80]
    return None


def _build_pilot_closeout_markdown(report: PilotReadinessReportResponse) -> str:
    power = report.power_upgrade_evidence
    completion = report.scenario_completion
    next_scenario = next((item for item in report.scenario_statuses if item.id == completion.next_scenario_id), None)
    lines = [
        "# Pilot Closeout Report",
        "",
        "## Pilot Status",
        f"- Status: {report.status}",
        f"- Window: {report.window_days}D",
        f"- Subject: {report.subject or 'global'}",
        f"- Team: {report.team_subject or 'all teams'}",
        f"- Completed scenarios: {completion.completed}/{completion.total}",
        f"- Runs completed: {report.runs_completed}",
        f"- Evidence-exportable runs: {report.evidence_exportable_runs}",
        f"- Ledger-valid runs: {report.ledger_valid_runs}",
        f"- Checkpointed runs: {report.checkpointed_runs}",
        "",
        "## Buyer Review Status",
        f"- Buyer review: {'Ready' if completion.ready_for_buyer_review else 'Not ready'}",
        f"- Next scenario: {next_scenario.name if next_scenario else 'None'}",
        f"- Needs evidence: {completion.needs_evidence}",
        f"- Missing scenarios: {completion.missing}",
        "",
        "## Value Generated",
        f"- Estimated value: ${report.estimated_value_usd}",
        f"- Review time saved: {report.review_time_saved_minutes} minutes",
        f"- Audit time saved: {report.audit_time_saved_minutes} minutes",
        f"- Blocked / needs-review runs: {report.blocked_or_needs_review_runs}",
        "",
        "## Scenario Completion",
    ]
    for scenario in report.scenario_statuses:
        lines.append(
            f"- {scenario.name}: {scenario.status} "
            f"(runs={scenario.completed_runs}, evidence={scenario.evidence_exportable_runs}, "
            f"ledger={scenario.ledger_valid_runs}, checkpoints={scenario.checkpointed_runs})"
        )
    lines.extend(
        [
            "",
            "## Why Power",
            f"- Power-required scenario runs: {power.power_required_runs}",
            f"- Approval-required runs: {power.approval_required_runs}",
            f"- Evidence-exportable runs: {power.evidence_exportable_runs}",
            f"- Ledger-valid runs: {power.ledger_valid_runs}",
            f"- Review + audit time saved: {power.review_audit_time_saved_minutes} minutes",
            f"- Recommendation: {power.recommendation}",
            "",
            "## Next Buyer Action",
        ]
    )
    lines.extend(f"- {item}" for item in report.recommendations)
    return "\n".join(lines).strip() + "\n"


def _latest_profiles(db: Session, *, subject: str | None = None) -> list[SubscriptionProfile]:
    query = db.query(SubscriptionProfile)
    if subject:
        query = query.filter(SubscriptionProfile.subject == subject)
    rows = query.order_by(SubscriptionProfile.subject.asc(), SubscriptionProfile.updated_at.desc(), SubscriptionProfile.id.desc()).all()
    latest_by_subject: dict[str, SubscriptionProfile] = {}
    for row in rows:
        if row.subject not in latest_by_subject:
            latest_by_subject[row.subject] = row
    return list(latest_by_subject.values())


def _build_subscription_summary(profiles: list[SubscriptionProfile]) -> CommercialMetricsSubscriptionSummary:
    tier_distribution: dict[MonetizationTier, int] = {"free": 0, "pro": 0, "power": 0}
    status_distribution: dict[str, int] = {"inactive": 0, "active": 0, "past_due": 0, "canceled": 0}
    active_subjects = 0
    for profile in profiles:
        tier = profile.tier.value
        status = profile.status.value
        tier_distribution[tier] = tier_distribution.get(tier, 0) + 1  # type: ignore[literal-required]
        status_distribution[status] = status_distribution.get(status, 0) + 1
        if profile.status == SubscriptionStatus.active:
            active_subjects += 1
    return CommercialMetricsSubscriptionSummary(
        active_subjects=active_subjects,
        profile_count=len(profiles),
        tier_distribution=tier_distribution,
        status_distribution=status_distribution,  # type: ignore[arg-type]
    )


def _usage_counters_for_profiles(db: Session, profile_ids: list[int]) -> list[UsageCounter]:
    if not profile_ids:
        return []
    return db.query(UsageCounter).filter(UsageCounter.subscription_profile_id.in_(profile_ids)).all()


def _counter_limit(counters: list[UsageCounter], metric: UsageMetric) -> int:
    return sum(counter.limit for counter in counters if counter.metric == metric)


def _counter_used(counters: list[UsageCounter], metric: UsageMetric) -> int:
    return sum(counter.used for counter in counters if counter.metric == metric)


def _build_plan_usage(counters: list[UsageCounter]) -> CommercialMetricsPlanUsage:
    period_starts = [counter.period_start for counter in counters]
    period_ends = [counter.period_end for counter in counters]
    return CommercialMetricsPlanUsage(
        workflow_runs_used=_counter_used(counters, UsageMetric.workflow_runs),
        workflow_runs_limit=_counter_limit(counters, UsageMetric.workflow_runs),
        queued_runs_used=_counter_used(counters, UsageMetric.queued_runs),
        queued_runs_limit=_counter_limit(counters, UsageMetric.queued_runs),
        period_start=min(period_starts) if period_starts else None,
        period_end=max(period_ends) if period_ends else None,
    )


def _endpoint_for_usage_metric(metric: UsageMetric) -> str:
    if metric == UsageMetric.queued_runs:
        return "/api/orchestrations/queue/run"
    return "/api/orchestrations/run"


def _get_active_profile_for_usage(db: Session, *, subject: str, now) -> SubscriptionProfile | None:
    profile = _get_latest_profile_model(db, subject=subject)
    if profile is None or profile.status != SubscriptionStatus.active:
        return None
    if profile.current_period_end and profile.current_period_end <= now:
        return None
    return profile


def _count_current_period_usage_logs(
    db: Session,
    *,
    subject: str,
    endpoint: str,
    period_start,
    period_end,
) -> int:
    expected_subject_ids = {subject, subject_id_for_entitlement_user(subject)}
    lower_bound = datetime.combine(period_start - timedelta(days=1), time.min)
    upper_bound = datetime.combine(period_end + timedelta(days=2), time.min)
    rows = (
        db.query(AgentRunLog)
        .filter(
            AgentRunLog.task_type == "monetization.usage_recorded",
            AgentRunLog.created_at >= lower_bound,
            AgentRunLog.created_at < upper_bound,
        )
        .order_by(AgentRunLog.created_at.desc(), AgentRunLog.id.desc())
        .all()
    )
    total = 0
    for row in rows:
        payload = _log_payload(row)
        if payload.get("endpoint") != endpoint:
            continue
        if payload.get("subject_id") not in expected_subject_ids:
            continue
        if endpoint == "/api/orchestrations/queue/run" and not isinstance(payload.get("queue_job_id"), int):
            continue
        if endpoint == "/api/orchestrations/run" and not isinstance(payload.get("orchestration_id"), int):
            continue
        business_day = business_date_from_utc(row.created_at)
        if period_start <= business_day <= period_end:
            total += 1
    return total


def _list_monetization_logs(
    db: Session,
    *,
    window_start,
    subject: str | None,
    task_types: set[str],
) -> list[AgentRunLog]:
    query = db.query(AgentRunLog).filter(AgentRunLog.created_at >= window_start, AgentRunLog.task_type.in_(task_types))
    rows = query.order_by(AgentRunLog.created_at.desc(), AgentRunLog.id.desc()).all()
    if not subject:
        return rows
    expected_subject_ids = {subject, subject_id_for_entitlement_user(subject)}
    return [row for row in rows if _log_payload(row).get("subject_id") in expected_subject_ids]


def _log_payload(log: AgentRunLog) -> dict[str, object]:
    return _safe_json_dict(log.input_summary)


def _list_metric_orchestrations(
    db: Session,
    *,
    window_start,
    subject: str | None,
    subject_orchestration_ids: set[int],
) -> list[WorkflowOrchestration]:
    if subject and not subject_orchestration_ids:
        return []
    query = db.query(WorkflowOrchestration).filter(WorkflowOrchestration.created_at >= window_start)
    if subject:
        query = query.filter(WorkflowOrchestration.id.in_(subject_orchestration_ids))
    return query.order_by(WorkflowOrchestration.created_at.desc(), WorkflowOrchestration.id.desc()).all()


def _templates_by_id_for_orchestrations(
    db: Session,
    records: list[WorkflowOrchestration],
) -> dict[int, WorkflowTemplate]:
    template_ids = {
        template_id
        for template_id in (_template_id_from_request_json(record.request_json) for record in records)
        if template_id is not None
    }
    if not template_ids:
        return {}
    return {
        template.id: template
        for template in db.query(WorkflowTemplate).filter(WorkflowTemplate.id.in_(template_ids)).all()
    }


def _build_top_templates(
    records: list[WorkflowOrchestration],
    templates_by_id: dict[int, WorkflowTemplate],
) -> list[CommercialMetricsTopTemplate]:
    stats: dict[int | None, dict[str, object]] = {}
    for record in records:
        template_id = _template_id_from_request_json(record.request_json)
        template = templates_by_id.get(template_id) if template_id is not None else None
        policy = _template_policy_from_template(template) if template is not None else _policy_from_request_json(record.request_json)
        key = template.id if template is not None else None
        if key not in stats:
            stats[key] = {
                "template_id": key,
                "template_name": template.name if template is not None else "Ad hoc workflow",
                "runs": 0,
                "billable_work_units": 0,
                "required_tier": policy.required_tier,
                "risk_level": policy.risk_level,
                "approval_required": policy.approval_required,
            }
        stats[key]["runs"] = int(stats[key]["runs"]) + 1
        stats[key]["billable_work_units"] = int(stats[key]["billable_work_units"]) + policy.billable_work_units

    return [
        CommercialMetricsTopTemplate.model_validate(item)
        for item in sorted(
            stats.values(),
            key=lambda item: (-int(item["billable_work_units"]), -(int(item["template_id"] or 0))),
        )[:5]
    ]


def _build_roi_summary(
    records: list[WorkflowOrchestration],
    templates_by_id: dict[int, WorkflowTemplate],
    checkpoint_counts: dict[int, int],
) -> CommercialMetricsRoiSummary:
    totals = {
        "runs_with_roi": 0,
        "estimated_customer_value_usd": 0,
        "review_time_saved_minutes": 0,
        "audit_time_saved_minutes": 0,
        "blocked_risk_count": 0,
        "blocked_risk_value_usd": 0,
        "billable_work_units": 0,
    }
    template_stats: dict[int | None, dict[str, object]] = {}
    for record in records:
        if record.status not in {"success", "partial_success"}:
            continue
        summary = _summary_from_result_json(record.result_json)
        policy = _policy_for_record(record, templates_by_id)
        roi = compute_workflow_roi_evidence(
            risks=summary["risks"],
            decision=decision_from_summary_text(summary["conclusion"]),
            risk_level=policy.risk_level,
            approval_required=policy.approval_required,
            billable_work_units=policy.billable_work_units,
            checkpoint_count=checkpoint_counts.get(record.id, 0),
        )
        totals["runs_with_roi"] += 1
        totals["estimated_customer_value_usd"] += roi.estimated_customer_value_usd
        totals["review_time_saved_minutes"] += roi.review_time_saved_minutes
        totals["audit_time_saved_minutes"] += roi.audit_time_saved_minutes
        totals["blocked_risk_count"] += roi.blocked_risk_count
        totals["blocked_risk_value_usd"] += roi.blocked_risk_value_usd
        totals["billable_work_units"] += roi.billable_work_units

        template_id = _template_id_from_request_json(record.request_json)
        template = templates_by_id.get(template_id) if template_id is not None else None
        key = template.id if template is not None else None
        if key not in template_stats:
            template_stats[key] = {
                "template_id": key,
                "template_name": template.name if template is not None else "Ad hoc workflow",
                "runs": 0,
                "billable_work_units": 0,
                "estimated_customer_value_usd": 0,
            }
        template_stats[key]["runs"] = int(template_stats[key]["runs"]) + 1
        template_stats[key]["billable_work_units"] = int(template_stats[key]["billable_work_units"]) + roi.billable_work_units
        template_stats[key]["estimated_customer_value_usd"] = (
            int(template_stats[key]["estimated_customer_value_usd"]) + roi.estimated_customer_value_usd
        )

    breakdown = [
        CommercialMetricsRoiTemplateBreakdown.model_validate(item)
        for item in sorted(
            template_stats.values(),
            key=lambda item: (-int(item["estimated_customer_value_usd"]), -(int(item["template_id"] or 0))),
        )[:5]
    ]
    return CommercialMetricsRoiSummary(
        runs_with_roi=totals["runs_with_roi"],
        estimated_customer_value_usd=totals["estimated_customer_value_usd"],
        review_time_saved_minutes=totals["review_time_saved_minutes"],
        audit_time_saved_minutes=totals["audit_time_saved_minutes"],
        blocked_risk_count=totals["blocked_risk_count"],
        blocked_risk_value_usd=totals["blocked_risk_value_usd"],
        billable_work_units=totals["billable_work_units"],
        work_units_by_template=breakdown,
    )


def _policy_for_record(
    record: WorkflowOrchestration,
    templates_by_id: dict[int, WorkflowTemplate],
) -> WorkflowTemplatePolicy:
    template_id = _template_id_from_request_json(record.request_json)
    if template_id is not None and template_id in templates_by_id:
        return _template_policy_from_template(templates_by_id[template_id])
    return _policy_from_request_json(record.request_json)


def _summary_from_result_json(value: str) -> dict[str, object]:
    payload = _safe_json_dict(value)
    conclusion = payload.get("conclusion")
    risks = payload.get("risks")
    return {
        "conclusion": conclusion if isinstance(conclusion, str) else "",
        "risks": [risk for risk in risks if isinstance(risk, str)] if isinstance(risks, list) else [],
    }


def _build_commercial_events(
    db: Session,
    *,
    window_start,
    profile_ids: list[int],
    subject: str | None,
) -> list[CommercialMetricsEventSummary]:
    if subject and not profile_ids:
        return []
    query = db.query(MonetizationEvent).filter(MonetizationEvent.created_at >= window_start)
    if subject:
        query = query.filter(MonetizationEvent.subscription_profile_id.in_(profile_ids))
    counts: dict[str, int] = {}
    for event in query.order_by(MonetizationEvent.created_at.desc(), MonetizationEvent.id.desc()).all():
        payload = _safe_json_dict(event.event_json)
        action = payload.get("action")
        key = action if isinstance(action, str) and action.strip() else event.event_kind.value
        key = key.replace("_", " ")
        counts[key] = counts.get(key, 0) + 1
    return [
        CommercialMetricsEventSummary(action=action, count=count)
        for action, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _build_commercial_trend(
    *,
    generated_at,
    period_days: int,
    orchestration_records: list[WorkflowOrchestration],
    templates_by_id: dict[int, WorkflowTemplate],
    block_logs: list[AgentRunLog],
) -> list[CommercialMetricsTrendPoint]:
    date_keys = _date_keys(generated_at, period_days)
    stats = {
        key: {"date": key, "billable_work_units": 0, "audited_workflows": 0, "policy_blocks": 0}
        for key in date_keys
    }
    for record in orchestration_records:
        key = record.created_at.date().isoformat()
        if key not in stats:
            continue
        stats[key]["billable_work_units"] += _billable_work_units_from_request_json(record.request_json, templates_by_id)
        if record.status in {"success", "partial_success"}:
            stats[key]["audited_workflows"] += 1
    for log in block_logs:
        key = log.created_at.date().isoformat()
        if key in stats:
            stats[key]["policy_blocks"] += 1
    return [CommercialMetricsTrendPoint.model_validate(stats[key]) for key in date_keys]


def _build_commercial_anomaly_hints(
    *,
    subscription_summary: CommercialMetricsSubscriptionSummary,
    usage_summary: CommercialMetricsUsageSummary,
    policy_blocks: CommercialMetricsPolicyBlocks,
    billable_work_units: int,
) -> list[CommercialMetricsAnomalyHint]:
    hints: list[CommercialMetricsAnomalyHint] = []
    total_usage = usage_summary.workflow_runs_used + usage_summary.queued_runs_used
    if policy_blocks.quota_exceeded > 0:
        hints.append(
            CommercialMetricsAnomalyHint(
                code="quota_exceeded",
                severity="critical",
                message=f"{policy_blocks.quota_exceeded} quota block(s) need plan or limit review.",
            )
        )
    if policy_blocks.total >= max(3, total_usage):
        hints.append(
            CommercialMetricsAnomalyHint(
                code="policy_blocks_high",
                severity="warning",
                message=f"{policy_blocks.total} policy block(s) appeared in this window.",
            )
        )
    if subscription_summary.active_subjects > 0 and billable_work_units == 0:
        hints.append(
            CommercialMetricsAnomalyHint(
                code="no_billable_activity",
                severity="info",
                message="Active subscriptions exist, but no billable workflow units were recorded.",
            )
        )
    return hints


def _date_keys(now, days: int) -> list[str]:
    return [(now - timedelta(days=offset)).date().isoformat() for offset in range(days - 1, -1, -1)]


def _template_id_from_request_json(value: str) -> int | None:
    payload = _safe_json_dict(value)
    template_id = payload.get("template_id")
    return template_id if isinstance(template_id, int) else None


def _billable_work_units_from_request_json(value: str, templates_by_id: dict[int, WorkflowTemplate]) -> int:
    template_id = _template_id_from_request_json(value)
    if template_id is not None and template_id in templates_by_id:
        return _template_policy_from_template(templates_by_id[template_id]).billable_work_units
    return _policy_from_request_json(value).billable_work_units


def _policy_from_request_json(value: str) -> WorkflowTemplatePolicy:
    payload = _safe_json_dict(value)
    steps = payload.get("steps")
    active_steps = 1
    if isinstance(steps, list):
        active_steps = len([step for step in steps if isinstance(step, dict) and step.get("enabled", True)])
    return WorkflowTemplatePolicy(required_tier="pro", billable_work_units=max(1, active_steps))


def _template_policy_from_template(template: WorkflowTemplate) -> WorkflowTemplatePolicy:
    tags = _normalize_tags(json.loads(template.tags_json or "[]"))
    required_tier = _tag_value(tags, "tier") or "pro"
    risk_level = _tag_value(tags, "risk") or "medium"
    work_units = _int_tag_value(tags, "work-units")
    tool_scopes = [tag.split(":", 1)[1] for tag in tags if tag.startswith("tool:") and tag.split(":", 1)[1]]
    return WorkflowTemplatePolicy(
        required_tier=required_tier if required_tier in {"free", "pro", "power"} else "pro",  # type: ignore[arg-type]
        risk_level=risk_level if risk_level in VALID_TEMPLATE_RISKS else "medium",  # type: ignore[arg-type]
        approval_required="approval:required" in tags,
        allowed_tool_scopes=tool_scopes or ["none"],
        billable_work_units=work_units or 1,
    )


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for tag in tags:
        clean = tag.strip().lower()
        if clean and clean not in normalized:
            normalized.append(clean)
    return normalized


def _tag_value(tags: list[str], key: str) -> str | None:
    prefix = f"{key}:"
    for tag in tags:
        if tag.startswith(prefix):
            return tag.split(":", 1)[1].strip()
    return None


def _int_tag_value(tags: list[str], key: str) -> int | None:
    value = _tag_value(tags, key)
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _to_subscription_profile_read(profile: SubscriptionProfile) -> SubscriptionProfileRead:
    return SubscriptionProfileRead(
        id=profile.id,
        subject=profile.subject,
        tier=profile.tier,
        status=profile.status,
        billing_provider=profile.billing_provider,
        external_customer_id=profile.external_customer_id,
        external_subscription_id=profile.external_subscription_id,
        current_period_start=profile.current_period_start,
        current_period_end=profile.current_period_end,
        cancel_at_period_end=profile.cancel_at_period_end,
        entitlements=_safe_json_dict(profile.entitlements_json),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _to_monetization_event_read(event: MonetizationEvent) -> MonetizationEventRead:
    return MonetizationEventRead(
        id=event.id,
        subscription_profile_id=event.subscription_profile_id,
        usage_counter_id=event.usage_counter_id,
        event_kind=event.event_kind,
        event=_safe_json_dict(event.event_json),
        created_at=event.created_at,
    )


def _get_latest_profile_model(db: Session, *, subject: str) -> SubscriptionProfile | None:
    return (
        db.query(SubscriptionProfile)
        .filter(SubscriptionProfile.subject == subject)
        .order_by(SubscriptionProfile.updated_at.desc(), SubscriptionProfile.id.desc())
        .first()
    )


def _entitlements_for_tier(tier: str) -> dict[str, object]:
    return dict(TIER_ENTITLEMENTS[tier])


def _current_month_bounds(now) -> tuple:
    business_day = business_date_from_utc(now)
    period_start = business_day.replace(day=1)
    period_end = business_day.replace(day=monthrange(business_day.year, business_day.month)[1])
    return period_start, period_end


def _upsert_current_period_counters(
    db: Session,
    *,
    profile: SubscriptionProfile,
    entitlements: dict[str, object],
    now,
) -> list[UsageCounter]:
    period_start, period_end = _current_month_bounds(now)
    counters: list[UsageCounter] = []
    for metric in (UsageMetric.workflow_runs, UsageMetric.queued_runs):
        counter = (
            db.query(UsageCounter)
            .filter(
                UsageCounter.subscription_profile_id == profile.id,
                UsageCounter.metric == metric,
                UsageCounter.period_start == period_start,
                UsageCounter.period_end == period_end,
            )
            .order_by(UsageCounter.id.desc())
            .first()
        )
        if counter is None:
            counter = UsageCounter(
                subscription_profile_id=profile.id,
                metric=metric,
                period_start=period_start,
                period_end=period_end,
                used=0,
                limit=int(entitlements.get(metric.value, 0) or 0),
                created_at=now,
                updated_at=now,
            )
            db.add(counter)
        else:
            counter.limit = int(entitlements.get(metric.value, counter.limit) or counter.limit)
            counter.updated_at = now
        counters.append(counter)
    db.flush()
    return counters


def _append_subscription_event(
    db: Session,
    *,
    profile: SubscriptionProfile,
    action: str,
    now,
    payload: dict[str, object],
) -> MonetizationEvent:
    event = MonetizationEvent(
        subscription_profile_id=profile.id,
        usage_counter_id=None,
        event_kind=MonetizationEventKind.subscription_changed,
        event_json=json.dumps({"version": 1, **payload}, sort_keys=True, separators=(",", ":")),
        created_at=now,
    )
    db.add(event)
    db.flush()
    return event


def _safe_json_dict(value: str) -> dict[str, object]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
