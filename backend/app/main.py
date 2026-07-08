"""SwingLens API entrypoint.

    uvicorn app.main:app --reload

`create_app` is a factory so tests (and future deployments) can inject
their own Settings; the module-level `app` uses environment configuration.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, swings
from app.api.websockets import progress
from app.config import Settings, get_settings
from app.models.database import create_session_factory
from app.services.storage import get_storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title="SwingLens API",
        description="Golf swing analysis: pose estimation, phase detection, "
                    "biomechanical metrics, and AI coaching feedback.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.settings = settings
    app.state.session_factory = create_session_factory(settings)
    app.state.storage = get_storage(settings)

    app.include_router(health.router, prefix=settings.api_v1_prefix)
    app.include_router(swings.router, prefix=settings.api_v1_prefix)
    app.include_router(progress.router)
    return app


app = create_app()
