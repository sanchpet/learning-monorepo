"""Golden-set: live classification quality against the real model.

This is the closed-loop done-criterion. structured output guarantees the FORM of
the answer; only golden examples can verify its CORRECTNESS (the right intent and
the right target). Each case fixes a quality bug we saw live: target = resource
NAME not kind, no intent bleed from history, pronoun -> most recent resource.

Gated by RUN_LIVE=1 so the default `pytest` (offline) never spends credits:

    RUN_LIVE=1 uv run pytest tests/test_classification_live.py -q

The key is read from .env by pydantic-settings; it never appears in code.
"""

import asyncio
import os

import pytest

from app.core.config import get_settings
from app.core.container import Container
from app.schemas.intent import ClassifyRequest, DialogMessage, HomelabIntent

requires_live = pytest.mark.skipif(
    os.environ.get("RUN_LIVE") != "1",
    reason="live LLM test — set RUN_LIVE=1 to run (spends OpenRouter credits)",
)

HI = HomelabIntent

# query, history (list of (role, content)), expected intent set, expected targets
GOLDEN: list[dict] = [
    {
        "query": "restart the postgres deployment",
        "intents": {HI.RESTART},
        "targets": {HI.RESTART: "postgres"},
    },
    {
        "query": "tail the logs for the grafana pod",
        "intents": {HI.LOGS},
        "targets": {HI.LOGS: "grafana"},
    },
    {
        "query": "reconcile the apps kustomization",
        "intents": {HI.RECONCILE},
        "targets": {HI.RECONCILE: "apps"},
    },
    {"query": "what is a flux kustomization?", "intents": {HI.EXPLAIN}},
    {"query": "what did I do last summer?", "intents": {HI.OTHER}},
    {"query": "is the cluster healthy?", "intents": {HI.STATUS}},
    {
        "query": "why is the cert-manager pod crashlooping?",
        "intents": {HI.DIAGNOSE},
        "targets": {HI.DIAGNOSE: "cert-manager"},
    },
    {
        "query": "restart nginx and show its logs",
        "intents": {HI.RESTART, HI.LOGS},
        "targets": {HI.RESTART: "nginx", HI.LOGS: "nginx"},
    },
    {
        "query": "reconcile the infra kustomization and restart the redis deployment",
        "intents": {HI.RECONCILE, HI.RESTART},
        "targets": {HI.RECONCILE: "infra", HI.RESTART: "redis"},
    },
    # context: pronoun resolves to the most recently mentioned resource
    {
        "history": [("user", "restart the redis deployment")],
        "query": "now show me its logs",
        "intents": {HI.LOGS},
        "targets": {HI.LOGS: "redis"},
    },
    # context: NO intent bleed — past 'reconcile' must not leak into a restart-only request
    {
        "history": [("user", "reconcile the apps kustomization")],
        "query": "restart the postgres deployment",
        "intents": {HI.RESTART},
        "targets": {HI.RESTART: "postgres"},
    },
]


@pytest.mark.live
@requires_live
def test_golden_classification() -> None:
    settings = get_settings()

    async def run() -> list[str]:
        container = Container.from_settings(settings)
        failures: list[str] = []
        try:
            for case in GOLDEN:
                history = [DialogMessage(role=r, content=c) for r, c in case.get("history", [])]
                req = ClassifyRequest(query=case["query"], history=history)
                res = await container.intent_service.classify(req)

                got = {item.intent for item in res.intents}
                if got != case["intents"]:
                    failures.append(
                        f"{case['query']!r}: intents {got} != expected {case['intents']}"
                    )
                    continue

                for intent, expected_target in case.get("targets", {}).items():
                    item = next(i for i in res.intents if i.intent == intent)
                    actual = (item.target or "").lower()
                    if expected_target.lower() not in actual:
                        failures.append(
                            f"{case['query']!r}: {intent.value} target {item.target!r} "
                            f"does not contain {expected_target!r}"
                        )
        finally:
            await container.close()
        return failures

    failures = asyncio.run(run())
    assert not failures, f"{len(failures)}/{len(GOLDEN)} golden checks failed:\n" + "\n".join(
        failures
    )
