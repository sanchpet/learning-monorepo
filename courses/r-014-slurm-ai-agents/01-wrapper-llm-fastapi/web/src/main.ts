// Контракт фронта = тот же контракт, что Pydantic-схемы бэкенда
// (app/schemas/intent.py). Это цена развязки SPA <-> API: форма дублируется на
// двух языках. Меняешь бэкенд-схему — меняешь и эти типы. (Зрелый путь — генерить
// эти типы из OpenAPI-схемы FastAPI; для учебного модуля держим вручную и осознанно.)

type HomelabIntent =
  | 'reconcile'
  | 'status'
  | 'restart'
  | 'logs'
  | 'diagnose'
  | 'explain'
  | 'other'

interface IntentItem {
  intent: HomelabIntent
  target: string | null
  confidence: number
  reasoning: string
}

interface PlannedAction {
  intent: HomelabIntent
  target: string | null
  command: string | null
  confidence: number
}

interface ClassifyResponse {
  intents: IntentItem[]
  needs_clarification: boolean
  plan: PlannedAction[]
}

interface DialogMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

const form = document.querySelector<HTMLFormElement>('#form')!
const queryInput = document.querySelector<HTMLInputElement>('#query')!
const out = document.querySelector<HTMLDivElement>('#out')!

// Историю диалога копим на клиенте и шлём при каждом запросе: бэкенд stateless
// (как мы разбирали — контекст несёт вызывающий, не сервер).
// Имя НЕ `history`: оно столкнулось бы с глобальным window.history (DOM-тип History).
const dialogHistory: DialogMessage[] = []

form.addEventListener('submit', async (event) => {
  event.preventDefault()
  const query = queryInput.value.trim()
  if (!query) return
  queryInput.value = ''

  try {
    const res = await fetch('/api/v1/classify', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query, history: dialogHistory }),
    })
    if (!res.ok) {
      renderError(query, `${res.status} ${await res.text()}`)
      return
    }
    const data = (await res.json()) as ClassifyResponse
    dialogHistory.push({ role: 'user', content: query })
    renderResult(query, data)
  } catch (err) {
    renderError(query, String(err))
  }
})

function renderResult(query: string, data: ClassifyResponse): void {
  const intents = data.intents
    .map(
      (i) =>
        `<li><b>${i.intent}</b>${i.target ? ` → <code>${esc(i.target)}</code>` : ''}` +
        ` <span class="conf">${Math.round(i.confidence * 100)}%</span>` +
        `<br /><small>${esc(i.reasoning)}</small></li>`,
    )
    .join('')

  const plan = data.plan
    .map(
      (p) =>
        `<li><b>${p.intent}</b>: ` +
        (p.command ? `<code>${esc(p.command)}</code>` : '<i>нет команды</i>') +
        '</li>',
    )
    .join('')

  const clarification = data.needs_clarification
    ? '<p class="warn">⚠ нужно уточнение — не хватает target</p>'
    : ''

  out.insertAdjacentHTML(
    'afterbegin',
    `<section class="card">
      <div class="q">▸ ${esc(query)}</div>
      ${clarification}
      <h3>Интенты</h3><ul>${intents}</ul>
      <h3>Dry-run план</h3><ul class="plan">${plan}</ul>
    </section>`,
  )
}

function renderError(query: string, detail: string): void {
  out.insertAdjacentHTML(
    'afterbegin',
    `<section class="card err">
      <div class="q">▸ ${esc(query)}</div>
      <p>Ошибка: ${esc(detail)}</p>
    </section>`,
  )
}

// На фронте защита от инъекции в DOM — НАША ответственность (вставляем строки от
// LLM в innerHTML). Это зеркало бэкендового решения: там Jinja autoescape мы
// выключали осознанно (это были не-HTML промпты), здесь — наоборот, экранируем.
function esc(value: string): string {
  const div = document.createElement('div')
  div.textContent = value
  return div.innerHTML
}
