from collections import deque
from threading import Lock
from time import monotonic

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

    if settings.rate_limit_enabled:
        rate_window = max(1, int(settings.rate_limit_window_seconds))
        rate_max_requests = max(1, int(settings.rate_limit_max_requests))
        buckets: dict[str, deque[float]] = {}
        buckets_lock = Lock()

        @app.middleware("http")
        async def basic_rate_limit(request, call_next):  # type: ignore[no-redef]
            path = request.url.path
            if request.method == "OPTIONS" or not path.startswith(settings.api_prefix):
                return await call_next(request)

            client_ip = request.client.host if request.client else "unknown"
            key = f"{request.method}:{client_ip}:{path}"
            now = monotonic()
            window_start = now - rate_window

            with buckets_lock:
                bucket = buckets.setdefault(key, deque())
                while bucket and bucket[0] < window_start:
                    bucket.popleft()

                if len(bucket) >= rate_max_requests:
                    retry_after = max(1, int(rate_window - (now - bucket[0])))
                    return JSONResponse(
                        status_code=429,
                        headers={"Retry-After": str(retry_after)},
                        content={"detail": "Too many requests. Please retry later."},
                    )

                bucket.append(now)

            return await call_next(request)

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
