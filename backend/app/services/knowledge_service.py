import json

from sqlalchemy.orm import Session

from app.models import NoteEntry
from app.schemas import NoteEntryCreate, NoteEntryRead, NoteEntryUpdate
from app.services.agent_log_service import log_agent_action


def create_note_entry(db: Session, payload: NoteEntryCreate) -> NoteEntryRead:
    note = NoteEntry(
        title=payload.title.strip(),
        content=payload.content.strip(),
        tags_json=json.dumps(_normalize_tags(payload.tags)),
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    log_agent_action(
        db,
        task_type="knowledge_note_created",
        input_summary=payload.title,
        output_summary=f"note_id={note.id}",
        status="success",
    )
    return _to_note_read(note)


def list_note_entries(db: Session, q: str | None = None, tag: str | None = None) -> list[NoteEntryRead]:
    notes = db.query(NoteEntry).order_by(NoteEntry.updated_at.desc()).all()
    filtered = [_to_note_read(note) for note in notes]

    if q and q.strip():
        query = q.strip().lower()
        filtered = [
            note
            for note in filtered
            if query in note.title.lower() or query in note.content.lower()
        ]

    if tag and tag.strip():
        tag_query = tag.strip().lower()
        filtered = [
            note
            for note in filtered
            if any(item.lower() == tag_query for item in note.tags)
        ]

    return filtered


def get_note_entry(db: Session, note_id: int) -> NoteEntryRead | None:
    note = db.get(NoteEntry, note_id)
    if note is None:
        return None
    return _to_note_read(note)


def update_note_entry(db: Session, note_id: int, payload: NoteEntryUpdate) -> NoteEntryRead | None:
    note = db.get(NoteEntry, note_id)
    if note is None:
        return None

    if payload.title is not None:
        note.title = payload.title.strip()
    if payload.content is not None:
        note.content = payload.content.strip()
    if payload.tags is not None:
        note.tags_json = json.dumps(_normalize_tags(payload.tags))

    db.add(note)
    db.commit()
    db.refresh(note)

    log_agent_action(
        db,
        task_type="knowledge_note_updated",
        input_summary=f"note_id={note_id}",
        output_summary=note.title,
        status="success",
    )
    return _to_note_read(note)


def delete_note_entry(db: Session, note_id: int) -> bool:
    note = db.get(NoteEntry, note_id)
    if note is None:
        return False

    db.delete(note)
    db.commit()

    log_agent_action(
        db,
        task_type="knowledge_note_deleted",
        input_summary=f"note_id={note_id}",
        output_summary="deleted",
        status="success",
    )
    return True


def _to_note_read(note: NoteEntry) -> NoteEntryRead:
    return NoteEntryRead(
        id=note.id,
        title=note.title,
        content=note.content,
        tags=_normalize_tags(json.loads(note.tags_json or "[]")),
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in tags:
        clean = item.strip()
        if clean and clean.lower() not in [existing.lower() for existing in normalized]:
            normalized.append(clean)
    return normalized
