"""Application entry point.

Step 2: read and validate settings at startup (fail-fast). If a required key is
missing the app will not boot, instead of failing in the middle of a request.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Runs once at process startup. Calling get_settings() triggers validation:
    # no key -> ValidationError -> uvicorn does not start.
    settings = get_settings()
    app.state.settings = settings
    yield
    # Resource cleanup on shutdown goes here (added in step 3).


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    app = FastAPI(title=resolved.app_name, version=resolved.app_version, lifespan=lifespan)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": resolved.app_env}

    return app


app = create_app()
