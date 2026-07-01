"""Read-only k8s incident agent (R-014 lesson-02).

Grows step by step. Right now it is a bare **connect** smoke: no tools, no cluster —
its only job is to prove the SDK agent loop boots, reaches a model *through the LiteLLM
gateway*, and streams back. Custom k8s tools land in the next step.
"""

import asyncio
import os
import shutil

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)
from dotenv import load_dotenv

load_dotenv()  # OPENROUTER_API_KEY / LITELLM_MASTER_KEY from .env (gitignored)


def _gateway_options(system_prompt: str) -> ClaudeAgentOptions:
    """Options that route the SDK through the local LiteLLM proxy (→ OpenRouter).

    The SDK drives the `claude` CLI, which reads auth from ITS env — so we point that
    env at the proxy instead of Anthropic. Two guards, learned from the course dry-run
    (kept even though this machine lacks the author's other footguns):
      - cli_path → a REAL `claude` binary: the SDK's *bundled* CLI can ignore
        ANTHROPIC_BASE_URL (#677); the system binary honours it. Verify with a
        kill-proxy test (agent must fail, not silently reach Anthropic).
      - setting_sources=[] → don't load ~/.claude config: isolation + no personal
        model pin leaking into this learning agent.
    """
    master_key = os.environ["LITELLM_MASTER_KEY"]  # fail loudly if .env is not filled
    return ClaudeAgentOptions(
        system_prompt=system_prompt,
        model="claude-sonnet",              # the model_list name in litellm/config.yaml
        cli_path=shutil.which("claude"),
        setting_sources=[],
        env={
            "ANTHROPIC_BASE_URL": os.environ.get("ANTHROPIC_BASE_URL", "http://localhost:4000"),
            "ANTHROPIC_API_KEY": master_key,  # the proxy's virtual key, not a real vendor key
            "ANTHROPIC_MODEL": "claude-sonnet",
        },
        max_turns=2,          # one reply needs one turn; 2 leaves slack
        max_budget_usd=0.05,  # cheap smoke cap
    )


async def main() -> None:
    opts = _gateway_options(
        "You are a read-only Kubernetes incident assistant. Answer in one short sentence."
    )
    # query() = one-shot: send a prompt, async-iterate the messages the loop emits.
    # (ClaudeSDKClient keeps a cross-turn session; a connect smoke needs no memory.)
    async for message in query(prompt="Reply with exactly: incident agent online.", options=opts):
        # Typed messages, not raw text. AssistantMessage carries the model's content
        # blocks; stream the text ones as they arrive.
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text, end="", flush=True)
        # ResultMessage terminates the run: subtype (success/error) + cost/usage.
        if isinstance(message, ResultMessage):
            print(f"\n--- {message.subtype} · ${message.total_cost_usd or 0:.4f} ---")


if __name__ == "__main__":
    asyncio.run(main())
