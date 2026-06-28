"""Composition root — wires concrete implementations together once, at startup.

Built from Settings in the FastAPI lifespan and stored on `app.state.container`;
request handlers pull dependencies from it (see app/api/dependencies.py). This is
manual dependency injection: construction lives in one place, the rest of the code
receives ready objects instead of building them.
"""

from dataclasses import dataclass

from openai import AsyncOpenAI

from app.core.config import Settings
from app.infra.llm.openrouter_client import OpenRouterLLMClient
from app.services.intent_service import IntentClassificationService


@dataclass(slots=True)
class Container:
    llm_client: OpenRouterLLMClient
    intent_service: IntentClassificationService

    @classmethod
    def from_settings(cls, settings: Settings) -> "Container":
        openai_client = AsyncOpenAI(
            api_key=settings.openrouter_api_key.get_secret_value(),
            base_url=str(settings.openrouter_base_url),
            timeout=settings.request_timeout_seconds,
            default_headers=_build_openrouter_headers(settings),
        )
        llm_client = OpenRouterLLMClient(openai_client, model=settings.openrouter_model)
        return cls(
            llm_client=llm_client,
            intent_service=IntentClassificationService(llm_client=llm_client),
        )

    async def close(self) -> None:
        await self.llm_client.close()


def _build_openrouter_headers(settings: Settings) -> dict[str, str]:
    headers: dict[str, str] = {}
    if settings.openrouter_referer:
        headers["HTTP-Referer"] = settings.openrouter_referer
    if settings.openrouter_title:
        headers["X-Title"] = settings.openrouter_title
    return headers
