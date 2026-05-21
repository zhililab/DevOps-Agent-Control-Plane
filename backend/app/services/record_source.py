from __future__ import annotations


SYSTEM_RECORD_SOURCES = {"smoke_check", "system"}


def normalize_record_source(value: str | None) -> str:
    if value is None:
        return "user"
    normalized = value.strip().lower().replace("-", "_")[:64]
    if normalized in {"smoke_check", "system", "user"}:
        return normalized
    return "user"
