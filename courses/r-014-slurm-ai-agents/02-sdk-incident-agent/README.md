# Модуль 02 — k8s incident-агент (Claude Agent SDK)

ДЗ урока-02 курса R-014, уровень **Hard**. Read-only агент, который диагностирует
упавший под в **боевом homelab-кластере**: `get_pod` → гипотеза → structured-сверка
`validate_diagnosis` → `report_diagnosis` (pydantic) → runbook. Ходит через
LiteLLM-прокси (gateway + fallback + учёт стоимости).

> Разбор материала, уточнения против упрощений курса и полный дизайн —
> в vault: `WP-059-k8s-incident-agent` (карточка РП) и `r014-01` (учебная заметка).

## Безопасность (defense-in-depth)

Мишень — **живой** кластер, поэтому «read-only» держится слоями, а не на регэкспе:

1. **Primary — RBAC.** Агент ходит под выделенным read-only ServiceAccount; мутация
   невозможна на уровне кластера. Манифесты — kustomize, применяются через Flux.
2. **Слой 2 — `PreToolUse`-hook** режет деструктивные команды до исполнения.
3. **Слой 3 — guard внутри `@tool`** ловит `subprocess`, который hook на SDK-Bash
   не видит.

## Стек

`claude-agent-sdk` (пин намеренный — поведение `is_error` зависит от версии `mcp`) ·
`litellm[proxy]` · Python 3.12 + uv. Зависимости слоятся по шагам.

## Запуск

_(добавляется по мере сборки — шаг connect первым)_
