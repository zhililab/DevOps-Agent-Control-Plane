from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Header, HTTPException

from app.config import get_settings


def require_evaluation_write_access(
    access_token: Annotated[str | None, Header(alias="X-Evaluation-Access")] = None,
) -> None:
    settings = get_settings()
    if not settings.effective_evaluation_write_protected:
        return

    configured_secret = settings.evaluation_write_secret.strip()
    if not configured_secret:
        raise HTTPException(status_code=503, detail="Evaluation write access is not configured.")
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing evaluation write access.")
    if not hmac.compare_digest(configured_secret, access_token.strip()):
        raise HTTPException(status_code=401, detail="Invalid evaluation write access.")
