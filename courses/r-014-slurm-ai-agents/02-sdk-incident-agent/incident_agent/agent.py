"""Read-only k8s incident agent (R-014 lesson-02).

Grows step by step. Right now it is a bare **connect** smoke: no tools, no cluster —
its only job is to prove the SDK agent loop boots, reaches a model, and streams back.
Custom k8s tools land in the next step.
"""

import asyncio

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)


async def main() -> None:
    # ClaudeAgentOptions = the agent's *policy* (tools, permissions, prompt, limits).
    # No mcp_servers / allowed_tools yet: with zero custom tools, query() is ALREADY an
    # agent loop — that's the whole point of the "connect" step. The caps make a smoke
    # run cheap and unable to spiral.
    opts = ClaudeAgentOptions(
        system_prompt=(
            "You are a read-only Kubernetes incident assistant. "
            "Answer in one short sentence."
        ),
        max_turns=2,          # one reply needs one turn; 2 leaves slack
        max_budget_usd=0.05,  # hard stop so a smoke can't burn money
    )

    # query() = one-shot: send a prompt, async-iterate the messages the loop emits.
    # (ClaudeSDKClient is the alternative — it keeps a session across turns; we don't
    # need memory for a connect smoke, so query() is the leaner choice.)
    async for message in query(prompt="Reply with exactly: incident agent online.", options=opts):
        # The SDK yields *typed* messages, not raw text. AssistantMessage carries the
        # model's content blocks; we stream the text ones as they arrive.
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text, end="", flush=True)
        # ResultMessage is the terminal message: subtype (success/error) + cost/usage.
        # Printing cost early builds the habit that will matter for the FinOps step.
        if isinstance(message, ResultMessage):
            print(f"\n--- {message.subtype} · ${message.total_cost_usd or 0:.4f} ---")


if __name__ == "__main__":
    asyncio.run(main())
