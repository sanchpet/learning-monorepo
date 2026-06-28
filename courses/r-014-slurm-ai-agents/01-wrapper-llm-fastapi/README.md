# 01 — Wrapper над LLM (FastAPI)

Первый самостоятельный модуль R-014. LLM-враппер, который **классифицирует**
запрос homelab-оператора по интентам и строит **dry-run план** — `classify-only`,
ничего не исполняет.

## Лейтмотив

> Как применить это с пользой для моей инфраструктуры и развить
> в практически применимое?

- **Ответ:** кейс — **homelab chatops**: NL-запрос → интенты (`reconcile`,
  `status`, `restart`, `logs`, `diagnose`, `explain`, `other`). Зерно на вынос —
  не классификация сама по себе, а **граница classify-only**: стохастический LLM
  решает *что* хочет оператор, детерминированный код (`services/commands.py`)
  решает *какая команда это сделала бы* — и останавливается. Тот же приём (LLM
  предлагает, политика исполняет) переносится на любой ops-ассистент.

## Кейс и пайплайн

1. **Stage 1 (стохастика):** LLM классифицирует запрос в `intents: list[...]`
   (мульти-интент — «restart ingress and show cert-manager logs» → `restart` +
   `logs`), извлекает `target`, ставит `confidence` и `needs_clarification`.
2. **Stage 2 (детерминизм):** каждый интент → dry-run команда по фиксированному
   шаблону. Нет живого кластера, нет kubeconfig, нет исполнения.

## Архитектура

```
app/
  api/         routes + DI (FastAPI Depends)
  core/        config (fail-fast) + container (composition root)
  infra/llm/   OpenRouter-клиент (Responses API, structured output)
  prompts/     system-промпт + Jinja2-билдер (templates/*.j2)
  schemas/     Pydantic-контракты (LLM-facing + API-facing)
  services/    intent_service (оркестрация) + commands (детерминированный план)
```

## Чему этот модуль учит сверх референса урока

1. **Мульти-интент** (`intents: list[IntentItem]`) — задача «со звёздочкой», в
   референсе один интент.
2. **Строгий fail-fast** конфига — ключ обязателен, валидируется на старте (в
   референсе дефолт `""` → падает уже в рантайме).
3. **Jinja2 `Environment` + кэш + файловые `.j2`** вместо `Template(string)` на
   каждый вызов; `autoescape=False` для LLM-промптов.
4. **Отделение стохастики от детерминизма** — `commands.py` тестируется офлайн,
   без API-ключа (`tests/test_commands.py`).

## Запуск

```bash
mise install                       # python 3.12 + uv
cp .env.example .env               # вписать OPENROUTER_API_KEY
uv sync
uv run uvicorn app.main:app --reload
```

```bash
curl -X POST http://localhost:8000/api/v1/classify \
  -H "Content-Type: application/json" \
  -d '{"query": "reconcile the apps kustomization and tail ingress logs", "history": []}'
```

## Тесты (офлайн, без ключа)

```bash
uv run pytest -q
```
