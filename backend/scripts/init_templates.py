#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.database import SessionLocal
from app.schemas import PromptTemplateCreate
from app.services.template_service import (
    import_prompt_templates_from_json,
    import_prompt_templates_from_sql,
    load_builtin_prompt_templates,
    render_builtin_prompt_templates_sql,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import prompt templates via JSON or SQL.")
    parser.add_argument("--mode", choices=["json", "sql"], default="json")
    parser.add_argument("--source", choices=["builtin", "file"], default="builtin")
    parser.add_argument("--file", default="", help="Path to JSON or SQL file when --source=file.")
    parser.add_argument("--upsert-by-name", action="store_true", default=True)
    parser.add_argument("--no-upsert-by-name", action="store_false", dest="upsert_by_name")
    parser.add_argument("--reset-existing", action="store_true", default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    db = SessionLocal()
    try:
        if args.mode == "json":
            items: list[PromptTemplateCreate]
            if args.source == "builtin":
                items = load_builtin_prompt_templates()
            else:
                if not args.file:
                    raise ValueError("Provide --file when --source=file for JSON mode.")
                payload = Path(args.file).read_text(encoding="utf-8")
                parsed = json.loads(payload)
                items = [PromptTemplateCreate.model_validate(item) for item in parsed]

            result = import_prompt_templates_from_json(
                db,
                items,
                upsert_by_name=args.upsert_by_name,
            )
        else:
            if args.source == "builtin":
                sql_content = render_builtin_prompt_templates_sql()
            else:
                if not args.file:
                    raise ValueError("Provide --file when --source=file for SQL mode.")
                sql_content = Path(args.file).read_text(encoding="utf-8")

            result = import_prompt_templates_from_sql(
                db,
                sql_content=sql_content,
                reset_existing=args.reset_existing,
            )

        print(
            f"[templates-import] mode={result.mode} imported={result.imported} "
            f"updated={result.updated} skipped={result.skipped} total={result.total}"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
