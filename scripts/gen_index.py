#!/usr/bin/env python3
"""Генератор авто-индекса README монорепо обучения.

Сканирует courses/ и переписывает дерево между маркерами
<!-- AUTO:INDEX --> ... <!-- /AUTO:INDEX --> в README.md.

Детерминированный скрипт (не агент): индекс — функция от файловой системы,
суждение LLM не нужно. Запускается из git pre-commit hook, поэтому навигация
не может разойтись с деревом каталогов. Источник истины — дерево, не README.
"""
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COURSES = ROOT / "courses"
README = ROOT / "README.md"
START = "<!-- AUTO:INDEX -->"
END = "<!-- /AUTO:INDEX -->"


def stack_of(d: Path) -> str:
    """Стек проекта из его mise.toml [tools] — для строки индекса."""
    f = d / "mise.toml"
    if not f.exists():
        return ""
    try:
        data = tomllib.loads(f.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return ""
    tools = data.get("tools", {})
    parts = []
    for name, ver in tools.items():
        if isinstance(ver, dict):
            parts.append(name)
        elif isinstance(ver, list):
            parts.append(f"{name} {', '.join(map(str, ver))}")
        else:
            parts.append(f"{name} {ver}")
    return ", ".join(parts)


def build_index() -> str:
    if not COURSES.exists():
        return "_Пока пусто._"
    lines: list[str] = []
    for course in sorted(p for p in COURSES.iterdir() if p.is_dir()):
        stack = stack_of(course)
        suffix = f" — стек: {stack}" if stack else ""
        lines.append(f"- **`courses/{course.name}/`**{suffix}")
        for item in sorted(p for p in course.iterdir() if p.is_dir()):
            est = stack_of(item)
            es = f" — {est}" if est else ""
            lines.append(f"  - `{item.name}/`{es}")
    return "\n".join(lines) if lines else "_Пока пусто._"


def main() -> int:
    if not README.exists():
        print("README.md не найден", file=sys.stderr)
        return 1
    text = README.read_text(encoding="utf-8")
    block = f"{START}\n{build_index()}\n{END}"
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        print(f"маркеры {START} / {END} не найдены в README.md", file=sys.stderr)
        return 1
    new = pattern.sub(block, text)
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("README: авто-индекс обновлён")
    else:
        print("README: авто-индекс без изменений")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
