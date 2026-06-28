"""Deterministic intent -> dry-run command mapping.

This is the *classify-only* boundary. The LLM decides WHAT the user wants (fuzzy,
stochastic); this module decides what command WOULD do it (fixed, testable) — and
stops there. Nothing is executed. Keeping this layer free of the LLM means we can
unit-test it with no API key (see tests/test_commands.py).

Commands are intentionally `--dry-run`-flavored suggestions, not ready-to-run lines.
"""

from app.schemas.intent import HomelabIntent, IntentItem, PlannedAction

# `{target}` is filled from the intent's slot. Intents with no template
# (explain/other) produce no command.
_COMMAND_TEMPLATES: dict[HomelabIntent, str] = {
    HomelabIntent.RECONCILE: "flux reconcile kustomization {target} -n flux-system --dry-run",
    HomelabIntent.STATUS: "flux get all -A",
    HomelabIntent.RESTART: "kubectl rollout restart deploy/{target}",
    HomelabIntent.LOGS: "kubectl logs deploy/{target} --tail=100",
    HomelabIntent.DIAGNOSE: "kubectl describe {target}",
}

# Intents whose command is meaningless without a concrete target.
_TARGET_REQUIRED: frozenset[HomelabIntent] = frozenset(
    {
        HomelabIntent.RECONCILE,
        HomelabIntent.RESTART,
        HomelabIntent.LOGS,
        HomelabIntent.DIAGNOSE,
    }
)

_TARGET_PLACEHOLDER = "<target>"


def build_action(item: IntentItem) -> PlannedAction:
    template = _COMMAND_TEMPLATES.get(item.intent)
    if template is None:
        command = None
    else:
        # When a required target is missing, render a visible placeholder rather
        # than a runnable command — the response also flags needs_clarification.
        target = item.target or (_TARGET_PLACEHOLDER if item.intent in _TARGET_REQUIRED else "")
        command = template.format(target=target)

    return PlannedAction(
        intent=item.intent,
        target=item.target,
        command=command,
        confidence=item.confidence,
    )


def build_plan(items: list[IntentItem]) -> list[PlannedAction]:
    return [build_action(item) for item in items]
