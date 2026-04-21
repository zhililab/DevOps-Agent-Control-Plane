import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models import PromptTemplate
from app.schemas import (
    PromptTemplateCreate,
    PromptTemplateImportResponse,
    PromptTemplateRead,
    PromptTemplateUpdate,
)
from app.services.agent_log_service import log_agent_action

_BOOTSTRAP_JSON_PATH = Path(__file__).resolve().parents[1] / "bootstrap" / "prompt_templates_v1.json"


@dataclass
class _ImportCounters:
    imported: int = 0
    updated: int = 0
    skipped: int = 0


def create_prompt_template(db: Session, payload: PromptTemplateCreate) -> PromptTemplateRead:
    template = PromptTemplate(
        name=payload.name.strip(),
        description=payload.description.strip(),
        body=payload.body.strip(),
        tags_json=json.dumps(_normalize_tags(payload.tags)),
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    log_agent_action(
        db,
        task_type="prompt_template_created",
        input_summary=payload.name,
        output_summary=f"template_id={template.id}",
        status="success",
    )
    return _to_template_read(template)


def list_prompt_templates(
    db: Session, q: str | None = None, tag: str | None = None
) -> list[PromptTemplateRead]:
    templates = db.query(PromptTemplate).order_by(PromptTemplate.updated_at.desc()).all()
    filtered = [_to_template_read(item) for item in templates]

    if q and q.strip():
        query = q.strip().lower()
        filtered = [
            template
            for template in filtered
            if query in template.name.lower()
            or query in template.description.lower()
            or query in template.body.lower()
        ]

    if tag and tag.strip():
        tag_query = tag.strip().lower()
        filtered = [
            template
            for template in filtered
            if any(item.lower() == tag_query for item in template.tags)
        ]

    return filtered


def get_prompt_template(db: Session, template_id: int) -> PromptTemplateRead | None:
    template = db.get(PromptTemplate, template_id)
    if template is None:
        return None
    return _to_template_read(template)


def update_prompt_template(
    db: Session, template_id: int, payload: PromptTemplateUpdate
) -> PromptTemplateRead | None:
    template = db.get(PromptTemplate, template_id)
    if template is None:
        return None

    if payload.name is not None:
        template.name = payload.name.strip()
    if payload.description is not None:
        template.description = payload.description.strip()
    if payload.body is not None:
        template.body = payload.body.strip()
    if payload.tags is not None:
        template.tags_json = json.dumps(_normalize_tags(payload.tags))

    db.add(template)
    db.commit()
    db.refresh(template)

    log_agent_action(
        db,
        task_type="prompt_template_updated",
        input_summary=f"template_id={template_id}",
        output_summary=template.name,
        status="success",
    )
    return _to_template_read(template)


def delete_prompt_template(db: Session, template_id: int) -> bool:
    template = db.get(PromptTemplate, template_id)
    if template is None:
        return False

    db.delete(template)
    db.commit()

    log_agent_action(
        db,
        task_type="prompt_template_deleted",
        input_summary=f"template_id={template_id}",
        output_summary="deleted",
        status="success",
    )
    return True


def load_builtin_prompt_templates() -> list[PromptTemplateCreate]:
    raw_items = json.loads(_BOOTSTRAP_JSON_PATH.read_text(encoding="utf-8"))
    return [PromptTemplateCreate.model_validate(item) for item in raw_items]


def render_builtin_prompt_templates_sql() -> str:
    records = load_builtin_prompt_templates()
    statements: list[str] = []
    for item in records:
        name = _escape_sql_literal(item.name.strip())
        description = _escape_sql_literal(item.description.strip())
        body = _escape_sql_literal(item.body.strip())
        tags_json = _escape_sql_literal(json.dumps(_normalize_tags(item.tags)))

        statements.append(
            "INSERT INTO prompt_templates (name, description, body, tags_json, created_at, updated_at) "
            f"VALUES ('{name}', '{description}', '{body}', '{tags_json}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);"
        )
    return "\n".join(statements)


def import_prompt_templates_from_json(
    db: Session,
    items: list[PromptTemplateCreate],
    upsert_by_name: bool = True,
) -> PromptTemplateImportResponse:
    counters = _ImportCounters()
    for payload in items:
        existing = None
        if upsert_by_name:
            existing = (
                db.query(PromptTemplate)
                .filter(func.lower(PromptTemplate.name) == payload.name.strip().lower())
                .first()
            )

        if existing is None:
            template = PromptTemplate(
                name=payload.name.strip(),
                description=payload.description.strip(),
                body=payload.body.strip(),
                tags_json=json.dumps(_normalize_tags(payload.tags)),
            )
            db.add(template)
            counters.imported += 1
            continue

        existing.description = payload.description.strip()
        existing.body = payload.body.strip()
        existing.tags_json = json.dumps(_normalize_tags(payload.tags))
        db.add(existing)
        counters.updated += 1

    db.commit()

    total = len(items)
    counters.skipped = total - counters.imported - counters.updated
    log_agent_action(
        db,
        task_type="prompt_templates_imported_json",
        input_summary=f"total={total}",
        output_summary=f"imported={counters.imported},updated={counters.updated},skipped={counters.skipped}",
        status="success",
    )
    return PromptTemplateImportResponse(
        mode="json",
        imported=counters.imported,
        updated=counters.updated,
        skipped=counters.skipped,
        total=total,
    )


def import_prompt_templates_from_sql(
    db: Session,
    sql_content: str,
    reset_existing: bool = False,
) -> PromptTemplateImportResponse:
    if reset_existing:
        db.query(PromptTemplate).delete()
        db.commit()

    before_count = db.query(PromptTemplate).count()
    statements = _split_sql_statements(sql_content)
    for statement in statements:
        lowered = statement.strip().lower()
        if not lowered.startswith("insert into prompt_templates"):
            raise ValueError("Only INSERT INTO prompt_templates statements are allowed.")
        db.execute(text(statement))

    db.commit()
    after_count = db.query(PromptTemplate).count()
    imported = max(0, after_count - before_count)
    total = len(statements)
    skipped = max(0, total - imported)

    log_agent_action(
        db,
        task_type="prompt_templates_imported_sql",
        input_summary=f"statements={total},reset_existing={reset_existing}",
        output_summary=f"imported={imported},skipped={skipped}",
        status="success",
    )
    return PromptTemplateImportResponse(
        mode="sql",
        imported=imported,
        updated=0,
        skipped=skipped,
        total=total,
    )


def _to_template_read(template: PromptTemplate) -> PromptTemplateRead:
    return PromptTemplateRead(
        id=template.id,
        name=template.name,
        description=template.description,
        body=template.body,
        tags=_normalize_tags(json.loads(template.tags_json or "[]")),
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in tags:
        clean = item.strip()
        if clean and clean.lower() not in [existing.lower() for existing in normalized]:
            normalized.append(clean)
    return normalized


def _escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _split_sql_statements(sql_content: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False
    i = 0

    while i < len(sql_content):
        char = sql_content[i]
        current.append(char)

        if char == "'":
            next_char = sql_content[i + 1] if i + 1 < len(sql_content) else ""
            if in_single_quote and next_char == "'":
                current.append(next_char)
                i += 1
            else:
                in_single_quote = not in_single_quote
        elif char == ";" and not in_single_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement[:-1].strip())
            current = []

        i += 1

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)

    return [statement for statement in statements if statement]
