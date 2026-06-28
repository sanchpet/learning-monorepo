"""Application entry point.

Step 3: wire the composition root (Container) into the app lifecycle and mount the
classification API. The container is built once at startup and closed on shutdown
(this is the "resource cleanup" the step-2 stub promised). A single exception
handler turns transport failures from the LLM client into a clean 502.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.core.config import Settings, get_settings
from app.core.container import Container
from app.infra.llm.openrouter_client import LLMClientError

# Built SPA lives at <project>/web/dist. __file__ = app/main.py -> parents[1] = project root.
_WEB_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # get_settings() triggers validation: no key -> ValidationError -> no boot.
    settings = get_settings()
    app.state.container = Container.from_settings(settings)
    yield
    await app.state.container.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    app = FastAPI(title=resolved.app_name, version=resolved.app_version, lifespan=lifespan)
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": resolved.app_env}

    @app.exception_handler(LLMClientError)
    async def llm_error_handler(_request: Request, exc: LLMClientError) -> JSONResponse:
        # Upstream (OpenRouter) failed -> 502 Bad Gateway, not a 500 on our side.
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    # Serve the built SPA from the same origin as the API, when it exists.
    # Mounted LAST so "/" cannot shadow /api/* and /health (routes added above win).
    # Absent in pure dev (the vite dev server proxies instead) -> skip, no error.
    if _WEB_DIST.is_dir():
        app.mount("/", StaticFiles(directory=_WEB_DIST, html=True), name="web")

    return app


app = create_app()
