"""USER-prompt builder, backed by a cached Jinja2 environment.

Delta vs the lesson reference: the reference compiles `Template(string)` on every
call, with the template inlined in Python. Here templates live in `templates/*.j2`
and the `Environment` is built once and cached. That is how prompts are managed in
real services — versionable template files, one compiled+cached environment.

`autoescape=False` on purpose: Jinja's autoescape is an HTML-injection guard. These
are LLM prompts, not HTML — escaping would turn quotes/brackets into `&quot;`/`&lt;`
and corrupt the prompt. `trim_blocks`/`lstrip_blocks` drop the blank lines that
`{% %}` control tags would otherwise leave behind.
"""

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.schemas.intent import DialogMessage, IntentItem, PlannedAction

_TEMPLATES_DIR = Path(__file__).parent / "templates"


@lru_cache
def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=False,  # LLM prompts, not HTML — see module docstring.
        trim_blocks=True,
        lstrip_blocks=True,
    )


def intent_analysis_prompt(query: str, history: list[DialogMessage]) -> str:
    template = _env().get_template("intent_analysis.j2")
    return template.render(query=query, history=history).strip()


def response_generation_prompt(
    query: str,
    intents: list[IntentItem],
    plan: list[PlannedAction],
    needs_clarification: bool,
) -> str:
    template = _env().get_template("response_generation.j2")
    return template.render(
        query=query,
        intents=intents,
        plan=plan,
        needs_clarification=needs_clarification,
    ).strip()
