"""FastAPI application entry point."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from apps.api.routes import router as events_router
from dualexis import __version__
from dualexis.core.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    _ = settings or Settings()
    app = FastAPI(
        title="DUALEXIS API",
        description=(
            "Privacy-preserving cognitive safety infrastructure API. "
            "Not a surveillance platform — structured events only."
        ),
        version=__version__,
    )
    app.include_router(events_router)

    @app.get("/health")
    async def root_health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


def run() -> None:
    settings = Settings()
    app = create_app(settings)
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    run()
