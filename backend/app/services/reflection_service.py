import json
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.models import ReflectionEntry
from app.schemas import (
    DailyReflectionHistoryResponse,
    DailyReflectionInput,
    DailyReflectionSavedResponse,
    DailyReflectionSummary,
    ReflectionEntryCreate,
    ReflectionEntryRead,
    ReflectionEntryUpdate,
)
from app.services.agent_log_service import log_agent_action

logger = logging.getLogger(__name__)


def create_reflection(db: Session, payload: ReflectionEntryCreate) -> ReflectionEntryRead:
    reflection = ReflectionEntry(
        entry_date=payload.entry_date,
        completed_json="[]",
        unfinished_json="[]",
        blockers_json="[]",
        notes="",
        summary=payload.summary,
        patterns=payload.patterns,
        next_actions=payload.next_actions,
        mood=payload.mood,
    )
    db.add(reflection)
    db.commit()
    db.refresh(reflection)
    return ReflectionEntryRead.model_validate(reflection)


def list_reflections(db: Session) -> list[ReflectionEntryRead]:
    items = db.query(ReflectionEntry).order_by(ReflectionEntry.entry_date.desc()).all()
    return [ReflectionEntryRead.model_validate(item) for item in items]


def update_reflection(
    db: Session, reflection_id: int, payload: ReflectionEntryUpdate
) -> ReflectionEntryRead | None:
    item = db.get(ReflectionEntry, reflection_id)
    if item is None:
        return None

    if payload.summary is not None:
        item.summary = payload.summary
    if payload.patterns is not None:
        item.patterns = payload.patterns
    if payload.next_actions is not None:
        item.next_actions = payload.next_actions
    if payload.mood is not None:
        item.mood = payload.mood

    db.add(item)
    db.commit()
    db.refresh(item)
    return ReflectionEntryRead.model_validate(item)


def create_daily_reflection(
    db: Session, reflection_input: DailyReflectionInput
) -> DailyReflectionSavedResponse:
    logger.info(
        "daily_reflection.request_received completed=%s unfinished=%s blockers=%s",
        len(reflection_input.completed),
        len(reflection_input.unfinished),
        len(reflection_input.blockers),
    )
    log_agent_action(
        db,
        task_type="daily_reflection_request",
        input_summary=json.dumps(reflection_input.model_dump(mode="json")),
        output_summary="request accepted",
        status="received",
    )

    generated = _generate_daily_reflection_summary(reflection_input)
    mood = _extract_mood(reflection_input.mood_or_notes)
    record = ReflectionEntry(
        entry_date=date.today(),
        completed_json=json.dumps(_normalize_lines(reflection_input.completed)),
        unfinished_json=json.dumps(generated.unfinished_items),
        blockers_json=json.dumps(_normalize_lines(reflection_input.blockers)),
        notes=reflection_input.mood_or_notes.strip(),
        summary=generated.day_summary,
        patterns="\n".join(generated.pattern_hints),
        next_actions="\n".join(generated.tomorrow_suggestions),
        mood=mood,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info("daily_reflection.persisted reflection_id=%s", record.id)
    log_agent_action(
        db,
        task_type="daily_reflection_persisted",
        input_summary=f"reflection_id={record.id}",
        output_summary=generated.day_summary,
        status="success",
    )

    return DailyReflectionSavedResponse(
        id=record.id,
        entry_date=record.entry_date,
        input=DailyReflectionInput(
            completed=_normalize_lines(reflection_input.completed),
            unfinished=generated.unfinished_items,
            blockers=_normalize_lines(reflection_input.blockers),
            mood_or_notes=reflection_input.mood_or_notes.strip(),
        ),
        summary=generated,
        created_at=record.created_at,
    )


def list_daily_reflections(db: Session) -> DailyReflectionHistoryResponse:
    records = db.query(ReflectionEntry).order_by(ReflectionEntry.created_at.desc()).all()
    logger.info("daily_reflection.history_requested total=%s", len(records))
    log_agent_action(
        db,
        task_type="daily_reflection_history_requested",
        input_summary="history list",
        output_summary=f"returned {len(records)} reflection(s)",
        status="success",
    )
    items = [_to_daily_reflection_response(record) for record in records]
    return DailyReflectionHistoryResponse(items=items)


def _to_daily_reflection_response(record: ReflectionEntry) -> DailyReflectionSavedResponse:
    input_completed = _load_json_lines(record.completed_json)
    input_unfinished = _load_json_lines(record.unfinished_json)
    input_blockers = _load_json_lines(record.blockers_json)
    pattern_hints = _split_text_lines(record.patterns)
    tomorrow_suggestions = _split_text_lines(record.next_actions)
    notes = (record.notes or "").strip()

    return DailyReflectionSavedResponse(
        id=record.id,
        entry_date=record.entry_date,
        input=DailyReflectionInput(
            completed=input_completed,
            unfinished=input_unfinished,
            blockers=input_blockers,
            mood_or_notes=notes or record.mood,
        ),
        summary=DailyReflectionSummary(
            day_summary=record.summary,
            unfinished_items=input_unfinished,
            pattern_hints=pattern_hints or ["No clear pattern yet. Keep tracking tomorrow."],
            tomorrow_suggestions=tomorrow_suggestions
            or ["Choose one unfinished item and schedule a focused start block."],
        ),
        created_at=record.created_at,
    )


def _generate_daily_reflection_summary(reflection_input: DailyReflectionInput) -> DailyReflectionSummary:
    completed = _normalize_lines(reflection_input.completed)
    unfinished = _normalize_lines(reflection_input.unfinished)
    blockers = _normalize_lines(reflection_input.blockers)
    notes = reflection_input.mood_or_notes.strip()

    if completed:
        completion_text = f"Completed {len(completed)} item(s), led by '{completed[0]}'."
    else:
        completion_text = "No completed items were captured today."

    if unfinished:
        unfinished_text = f"{len(unfinished)} item(s) remain unfinished."
    else:
        unfinished_text = "No unfinished carry-over items were recorded."

    blocker_text = (
        f"Blockers to watch: {', '.join(blockers[:2])}." if blockers else "No blockers explicitly reported."
    )
    note_text = f" Mood/notes: {notes}." if notes else ""

    day_summary = f"{completion_text} {unfinished_text} {blocker_text}{note_text}".strip()

    pattern_hints: list[str] = []
    if blockers:
        pattern_hints.append("Blockers repeated today; escalate early before deep work starts.")
    if unfinished and completed:
        pattern_hints.append("Execution moved, but closure lagged; protect a finish block tomorrow.")
    if unfinished and not completed:
        pattern_hints.append("Low closure signal today; reduce scope and commit to one must-finish item.")
    if not pattern_hints:
        pattern_hints.append("Steady day pattern; continue with the same planning cadence.")

    tomorrow_suggestions: list[str] = []
    if unfinished:
        tomorrow_suggestions.append(f"Start with unfinished item: {unfinished[0]}")
    if blockers:
        tomorrow_suggestions.append(f"Resolve or escalate blocker first: {blockers[0]}")
    if completed:
        tomorrow_suggestions.append(f"Reuse what worked from: {completed[0]}")
    if len(tomorrow_suggestions) < 2:
        tomorrow_suggestions.append("Set one clear outcome for tomorrow before ending the day.")

    return DailyReflectionSummary(
        day_summary=day_summary,
        unfinished_items=unfinished,
        pattern_hints=pattern_hints[:3],
        tomorrow_suggestions=tomorrow_suggestions[:3],
    )


def _normalize_lines(items: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in items:
        clean = item.strip()
        if clean and clean not in normalized:
            normalized.append(clean)
    return normalized


def _load_json_lines(payload: str) -> list[str]:
    if not payload:
        return []
    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return _normalize_lines([str(item) for item in loaded])


def _split_text_lines(value: str) -> list[str]:
    return _normalize_lines(value.split("\n"))


def _extract_mood(notes: str) -> str:
    text = notes.strip().lower()
    if not text:
        return "neutral"
    if "great" in text or "good" in text or "focused" in text:
        return "focused"
    if "stuck" in text or "blocked" in text or "frustrat" in text:
        return "strained"
    return "neutral"
