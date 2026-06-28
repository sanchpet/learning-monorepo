"""Application service: orchestrates one classification request.

Stage 1 (stochastic): ask the LLM to classify the request into intents.
Stage 2 (deterministic): turn each intent into a dry-run command via commands.py.
Stage 3 (stochastic): a second LLM call writes a conversational reply, grounded in
the stage-1 intents and the stage-2 plan (it does not reclassify or invent commands).

The service owns the sequence; it does not own transport (the LLM client) or the
command rules (commands.py). That keeps each piece independently testable.

Note: this costs TWO LLM calls per request (classify + respond). The reference
lesson does the same — the price of a chat reply on top of structured classification.
"""

from app.infra.llm.openrouter_client import OpenRouterLLMClient
from app.prompts.builder import intent_analysis_prompt, response_generation_prompt
from app.prompts.system import INTENT_ANALYSIS_SYSTEM_PROMPT, RESPONSE_GENERATION_SYSTEM_PROMPT
from app.schemas.intent import (
    AnswerLLMResponse,
    ClassificationLLMResponse,
    ClassifyRequest,
    ClassifyResponse,
)
from app.services.commands import build_plan


class IntentClassificationService:
    def __init__(self, llm_client: OpenRouterLLMClient) -> None:
        self._llm_client = llm_client

    async def classify(self, payload: ClassifyRequest) -> ClassifyResponse:
        # Stage 1 — classify.
        user_prompt = intent_analysis_prompt(query=payload.query, history=payload.history)
        analysis = await self._llm_client.complete_structured(
            system_prompt=INTENT_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            text_format=ClassificationLLMResponse,
        )

        # Stage 2 — deterministic dry-run plan.
        plan = build_plan(analysis.intents)

        # Stage 3 — conversational reply, grounded in stages 1 and 2.
        answer_prompt = response_generation_prompt(
            query=payload.query,
            intents=analysis.intents,
            plan=plan,
            needs_clarification=analysis.needs_clarification,
        )
        answer = await self._llm_client.complete_structured(
            system_prompt=RESPONSE_GENERATION_SYSTEM_PROMPT,
            user_prompt=answer_prompt,
            text_format=AnswerLLMResponse,
        )

        return ClassifyResponse(
            answer=answer.answer,
            intents=analysis.intents,
            needs_clarification=analysis.needs_clarification,
            plan=plan,
        )
