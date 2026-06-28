"""Thin wrapper over the OpenAI SDK pointed at OpenRouter.

One responsibility: take a system + user prompt and a Pydantic schema, and return
a validated instance of that schema (structured output). Transport errors are
mapped to a single `LLMClientError` so callers don't depend on OpenAI's exception
classes.

We use the *Chat Completions API* (`client.chat.completions.parse`) with
`response_format=<Model>`: the SDK sends the model's JSON Schema, the provider
constrains decoding to it, and `choices[0].message.parsed` comes back already
validated. Chat Completions is chosen over the newer Responses API on purpose —
it is GA (not beta on OpenRouter) and universally spoken (OpenRouter, LiteLLM,
Ollama, ...), so the provider stays a swappable detail behind this facade. We use
no Responses-only feature (server-side state, hosted tools), so there is nothing
to trade away. `extra_body` asks OpenRouter to only route to providers that
actually honor the structured-output parameters.
"""

import logging
from typing import TypeVar

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)
StructuredResponseT = TypeVar("StructuredResponseT", bound=BaseModel)


class LLMClientError(RuntimeError):
    pass


class OpenRouterLLMClient:
    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        text_format: type[StructuredResponseT],
        max_output_tokens: int = 800,
        temperature: float = 0.0,
    ) -> StructuredResponseT:
        try:
            completion = await self._client.chat.completions.parse(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=text_format,
                max_tokens=max_output_tokens,
                temperature=temperature,
                extra_body={"provider": {"require_parameters": True}},
            )
        except APIStatusError as exc:
            logger.warning("OpenRouter status=%s body=%s", exc.status_code, exc.response.text)
            raise LLMClientError("OpenRouter request failed") from exc
        except (APIConnectionError, APITimeoutError) as exc:
            logger.warning("OpenRouter connection failed: %r", exc)
            raise LLMClientError("OpenRouter request failed") from exc

        message = completion.choices[0].message
        # The model can decline to answer (safety, prompt-extraction attempts) —
        # that arrives as a refusal, not a parsed object. Treat it as a clean error.
        if message.refusal:
            raise LLMClientError(f"Model refused the request: {message.refusal}")

        parsed = message.parsed
        if parsed is None:
            raise LLMClientError("OpenRouter returned an unparseable structured response")

        return parsed

    async def close(self) -> None:
        await self._client.close()
