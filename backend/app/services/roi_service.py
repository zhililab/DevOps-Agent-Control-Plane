from __future__ import annotations

from typing import Literal

from app.schemas import WorkflowRoiEvidence


ENGINEERING_REVIEW_RATE_USD_PER_HOUR = 150
BLOCKED_RISK_VALUE_BY_LEVEL = {
    "low": 250,
    "medium": 1000,
    "high": 5000,
    "critical": 15000,
}


def decision_from_summary_text(summary: str) -> str:
    normalized = summary.lower()
    if "decision:" not in normalized:
        return "needs human review"
    decision = normalized.split("decision:", 1)[1].split(".", 1)[0].strip()
    if decision in {"approve", "block", "needs human review"}:
        return decision
    return "needs human review"


def compute_workflow_roi_evidence(
    *,
    risks: list[str],
    decision: str,
    risk_level: Literal["low", "medium", "high", "critical"],
    approval_required: bool,
    billable_work_units: int,
    checkpoint_count: int = 0,
) -> WorkflowRoiEvidence:
    safe_work_units = max(1, int(billable_work_units or 1))
    review_time_saved_minutes = safe_work_units * 6 + (15 if approval_required else 5)
    audit_time_saved_minutes = safe_work_units * 3 + min(20, max(0, checkpoint_count) * 2) + 10

    blocked_risk_count = sum(1 for risk in risks if "blocked risk" in risk.lower())
    if decision == "block":
        blocked_risk_count = max(blocked_risk_count, 1)
    if blocked_risk_count == 0 and approval_required and risk_level in {"high", "critical"}:
        blocked_risk_count = 1

    blocked_risk_value = blocked_risk_count * BLOCKED_RISK_VALUE_BY_LEVEL[risk_level]
    time_value = int(
        ((review_time_saved_minutes + audit_time_saved_minutes) / 60)
        * ENGINEERING_REVIEW_RATE_USD_PER_HOUR
        + 0.5
    )

    return WorkflowRoiEvidence(
        review_time_saved_minutes=review_time_saved_minutes,
        audit_time_saved_minutes=audit_time_saved_minutes,
        blocked_risk_count=blocked_risk_count,
        blocked_risk_value_usd=blocked_risk_value,
        estimated_customer_value_usd=blocked_risk_value + time_value,
        billable_work_units=safe_work_units,
        assumptions=[
            "Engineering review time is estimated at 6 minutes per billable work unit plus approval overhead.",
            "Audit time is estimated from work units and checkpoint-ready evidence.",
            "Blocked risk value uses low=$250, medium=$1000, high=$5000, critical=$15000 per blocked risk.",
            "ROI evidence is directional for buyer demos and pilot review, not billing data.",
        ],
    )
