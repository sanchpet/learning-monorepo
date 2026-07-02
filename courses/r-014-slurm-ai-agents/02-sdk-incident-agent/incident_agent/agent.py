"""Read-only k8s incident agent (R-014 lesson-02).

Grows step by step. Now: query() + a custom `get_pod` tool — the agent inspects a pod
(describe + events) under a read-only ServiceAccount and summarizes its health. Runs
through the local LiteLLM gateway (→ OpenRouter). Structured verify / report land next.
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

from incident_agent.tools import k8s_server

load_dotenv()  # OPENROUTER/LITELLM keys + KUBECONFIG (scoped read-only SA), all gitignored


def _gateway_options(system_prompt: str) -> ClaudeAgentOptions:
    """Options: route the SDK through the local LiteLLM proxy and expose the k8s tool.

    Gateway guards (from the course dry-run, kept though this machine lacks the rest):
      - cli_path → a REAL `claude` binary: the bundled CLI can ignore ANTHROPIC_BASE_URL
        (#677). Proven via the kill-proxy test.
      - setting_sources=[] → don't load ~/.claude config: isolation, no personal pin.
      - CLAUDE_CODE_MAX_OUTPUT_TOKENS: OpenRouter reserves credit by max_tokens; the CLI's
        default is huge → 402. Cap it.
    """
    master_key = os.environ["LITELLM_MASTER_KEY"]  # fail loudly if .env is not filled
    return ClaudeAgentOptions(
        system_prompt=system_prompt,
        model="claude-sonnet",              # the model_list name in litellm/config.yaml
        cli_path=shutil.which("claude"),
        setting_sources=[],
        mcp_servers={"k8s": k8s_server},
        allowed_tools=["mcp__k8s__get_pod"],  # auto-approve our read-only tool (no prompts)
        env={
            "ANTHROPIC_BASE_URL": os.environ.get("ANTHROPIC_BASE_URL", "http://localhost:4000"),
            "ANTHROPIC_API_KEY": master_key,   # the proxy's virtual key, not a real vendor key
            "ANTHROPIC_MODEL": "claude-sonnet",
            "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "1024",
        },
        max_turns=6,          # gather → reason → answer now spans a few turns
        max_budget_usd=0.50,  # a few CLI calls, each carrying the big system prompt
    )


async def main() -> None:
    opts = _gateway_options(
        "You are a read-only Kubernetes incident assistant. Use the get_pod tool to "
        "inspect a pod (describe + events) before answering. Read-only: never suggest or "
        "attempt any mutation. Summarize the pod's health in 2-3 sentences."
    )
    prompt = os.environ.get(
        "AGENT_PROMPT", "Inspect pod vault-0 in namespace vault and summarize its state."
    )
    async for message in query(prompt=prompt, options=opts):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text, end="", flush=True)
        if isinstance(message, ResultMessage):
            print(f"\n--- {message.subtype} · ${message.total_cost_usd or 0:.4f} ---")


if __name__ == "__main__":
    asyncio.run(main())
