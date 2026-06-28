"""Application service: orchestrates one classification request.

Stage 1 (stochastic): ask the LLM to classify the request into intents.
Stage 2 (deterministic): turn each intent into a dry-run command via commands.py.

The service owns the sequence; it does not own transport (the LLM client) or the
command rules (commands.py). That keeps each piece independently testable.
"""

from app.infra.llm.openrouter_client import OpenRouterLLMClient
from app.prompts.builder import intent_analysis_prompt
from app.prompts.system import INTENT_ANALYSIS_SYSTEM_PROMPT
from app.schemas.intent import ClassificationLLMResponse, ClassifyRequest, ClassifyResponse
from app.services.commands import build_plan


class IntentClassificationService:
    def __init__(self, llm_client: OpenRouterLLMClient) -> None:
        self._llm_client = llm_client

    async def classify(self, payload: ClassifyRequest) -> ClassifyResponse:
        user_prompt = intent_analysis_prompt(query=payload.query, history=payload.history)
        analysis = await self._llm_client.complete_structured(
            system_prompt=INTENT_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            text_format=ClassificationLLMResponse,
        )
        return ClassifyResponse(
            intents=analysis.intents,
            needs_clarification=analysis.needs_clarification,
            plan=build_plan(analysis.intents),
        )
