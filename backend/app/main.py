from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import knowledge, plans, profile, reflections, tasks, technical_analysis, templates
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(profile.router, prefix=settings.api_prefix)
    app.include_router(plans.router, prefix=settings.api_prefix)
    app.include_router(reflections.router, prefix=settings.api_prefix)
    app.include_router(tasks.router, prefix=settings.api_prefix)
    app.include_router(technical_analysis.router, prefix=settings.api_prefix)
    app.include_router(knowledge.router, prefix=settings.api_prefix)
    app.include_router(templates.router, prefix=settings.api_prefix)

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
