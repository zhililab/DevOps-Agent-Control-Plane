from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    PromptTemplateCreate,
    PromptTemplateImportJsonRequest,
    PromptTemplateImportResponse,
    PromptTemplateImportSqlRequest,
    PromptTemplateRead,
    PromptTemplateUpdate,
)
from app.services.template_service import (
    create_prompt_template,
    delete_prompt_template,
    get_prompt_template,
    import_prompt_templates_from_json,
    import_prompt_templates_from_sql,
    list_prompt_templates,
    load_builtin_prompt_templates,
    render_builtin_prompt_templates_sql,
    update_prompt_template,
)

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("", response_model=PromptTemplateRead)
def create_prompt_template_endpoint(
    payload: PromptTemplateCreate,
    db: Session = Depends(get_db),
) -> PromptTemplateRead:
    return create_prompt_template(db, payload)


@router.get("", response_model=list[PromptTemplateRead])
def list_prompt_templates_endpoint(
    q: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[PromptTemplateRead]:
    return list_prompt_templates(db, q=q, tag=tag)


@router.get("/init/json", response_model=list[PromptTemplateCreate])
def get_template_init_json() -> list[PromptTemplateCreate]:
    return load_builtin_prompt_templates()


@router.get("/init/sql", response_class=PlainTextResponse)
def get_template_init_sql() -> str:
    return render_builtin_prompt_templates_sql()


@router.post("/import/json", response_model=PromptTemplateImportResponse)
def import_templates_json_endpoint(
    payload: PromptTemplateImportJsonRequest,
    db: Session = Depends(get_db),
) -> PromptTemplateImportResponse:
    items = payload.items
    if payload.use_builtin:
        items = load_builtin_prompt_templates()
    return import_prompt_templates_from_json(db, items, upsert_by_name=payload.upsert_by_name)


@router.post("/import/sql", response_model=PromptTemplateImportResponse)
def import_templates_sql_endpoint(
    payload: PromptTemplateImportSqlRequest,
    db: Session = Depends(get_db),
) -> PromptTemplateImportResponse:
    sql_content = payload.sql
    if payload.use_builtin:
        sql_content = render_builtin_prompt_templates_sql()
    try:
        return import_prompt_templates_from_sql(db, sql_content, reset_existing=payload.reset_existing)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{template_id}", response_model=PromptTemplateRead)
def get_prompt_template_endpoint(
    template_id: int,
    db: Session = Depends(get_db),
) -> PromptTemplateRead:
    template = get_prompt_template(db, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return template


@router.put("/{template_id}", response_model=PromptTemplateRead)
def update_prompt_template_endpoint(
    template_id: int,
    payload: PromptTemplateUpdate,
    db: Session = Depends(get_db),
) -> PromptTemplateRead:
    template = update_prompt_template(db, template_id, payload)
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return template


@router.delete("/{template_id}", status_code=204)
def delete_prompt_template_endpoint(
    template_id: int,
    db: Session = Depends(get_db),
) -> Response:
    deleted = delete_prompt_template(db, template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return Response(status_code=204)
