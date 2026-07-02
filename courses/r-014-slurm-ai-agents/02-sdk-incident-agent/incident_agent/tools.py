"""Custom read-only k8s tools for the incident agent.

Registered via create_sdk_mcp_server → the SDK exposes each to the model as
`mcp__k8s__<name>`. They shell out to `kubectl`, which uses whatever KUBECONFIG the
agent PROCESS inherits — locally the scoped read-only SA kubeconfig, in a Pod the
mounted SA. Same code, different config source (the dev/prod parity we want).
"""

import subprocess

from claude_agent_sdk import create_sdk_mcp_server, tool


def _kubectl(*args: str) -> subprocess.CompletedProcess:
    # Hardcoded READ verbs only. The model supplies a pod name/namespace, never a verb,
    # so this tool can't be steered into a mutation. The read-only SA + ClusterRole are
    # the real boundary; this is belt-and-suspenders. (A destructive-verb guard matters
    # only once we add a Bash tool or user-influenced args — the PreToolUse hook does not
    # see this subprocess.)
    return subprocess.run(["kubectl", *args], capture_output=True, text=True, timeout=30)


@tool(
    "get_pod",
    "Read-only summary of a pod: `describe` output plus the pod's events.",
    {"name": str, "namespace": str},
)
async def get_pod(args):
    ns = args.get("namespace") or "default"
    describe = _kubectl("describe", "pod", args["name"], "-n", ns)
    if describe.returncode != 0:
        # is_error (not raise): the agent SEES the failure and can adjust; the loop stays
        # alive. Raising would kill it — the lesson footgun (see r014-01).
        return {"is_error": True, "content": [{"type": "text", "text": describe.stderr.strip()}]}
    events = _kubectl(
        "get", "events", "-n", ns, "--field-selector", f"involvedObject.name={args['name']}"
    )
    body = describe.stdout + "\n--- events ---\n" + events.stdout
    return {"content": [{"type": "text", "text": body}]}


k8s_server = create_sdk_mcp_server(name="k8s", version="1.0", tools=[get_pod])
