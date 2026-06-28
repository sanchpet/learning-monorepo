"""Offline tests for the deterministic command layer.

No API key, no network: this is exactly the part we *can* verify deterministically
(the closed-loop slice). The stochastic LLM classification is verified separately
against golden examples once a key is available.
"""

from app.schemas.intent import HomelabIntent, IntentItem
from app.services.commands import build_action, build_plan


def _item(intent: HomelabIntent, target: str | None = None) -> IntentItem:
    return IntentItem(intent=intent, target=target, confidence=0.9, reasoning="test")


def test_reconcile_fills_target() -> None:
    action = build_action(_item(HomelabIntent.RECONCILE, target="apps"))
    assert action.command == "flux reconcile kustomization apps -n flux-system --dry-run"


def test_explain_has_no_command() -> None:
    action = build_action(_item(HomelabIntent.EXPLAIN))
    assert action.command is None


def test_missing_required_target_renders_placeholder() -> None:
    action = build_action(_item(HomelabIntent.RESTART, target=None))
    assert action.command is not None
    assert "<target>" in action.command


def test_status_needs_no_target() -> None:
    action = build_action(_item(HomelabIntent.STATUS))
    assert action.command == "flux get all -A"


def test_build_plan_is_one_action_per_intent() -> None:
    items = [_item(HomelabIntent.RESTART, "ingress"), _item(HomelabIntent.LOGS, "cert-manager")]
    plan = build_plan(items)
    assert [a.intent for a in plan] == [HomelabIntent.RESTART, HomelabIntent.LOGS]
