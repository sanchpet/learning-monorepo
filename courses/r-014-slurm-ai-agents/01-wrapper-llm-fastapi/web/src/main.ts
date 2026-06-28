// Контракт фронта = Pydantic-схемы бэкенда (app/schemas/intent.py). Меняешь схему —
// меняешь и эти типы (цена развязки SPA <-> API; зрелый путь — генерить из OpenAPI).

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
  answer: string // stage 3 — разговорная реплика
  intents: IntentItem[] // debug — stage 1
  needs_clarification: boolean
  plan: PlannedAction[] // debug — stage 2
}

interface DialogMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

const form = document.querySelector<HTMLFormElement>('#form')!
const queryInput = document.querySelector<HTMLInputElement>('#query')!
const log = document.querySelector<HTMLDivElement>('#log')!
const debugToggle = document.querySelector<HTMLInputElement>('#debug')!

// История диалога копится на клиенте и шлётся при каждом запросе (бэкенд stateless).
// Шлём только реплики пользователя: классификатору они и нужны как контекст для
// разрешения ссылок; свой же ответ ассистента в контекст не возвращаем.
const dialogHistory: DialogMessage[] = []

// debug-режим переключает только CSS-класс на <body>; debug-разметка всегда в DOM,
// видимостью рулит стиль — не перерисовываем ленту при переключении тумблера.
debugToggle.addEventListener('change', () => {
  document.body.classList.toggle('debug-on', debugToggle.checked)
})

form.addEventListener('submit', async (event) => {
  event.preventDefault()
  const query = queryInput.value.trim()
  if (!query) return
  queryInput.value = ''
  appendUser(query)

  const pending = appendBot('…', null)
  try {
    const res = await fetch('/api/v1/classify', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query, history: dialogHistory }),
    })
    if (!res.ok) {
      pending.replaceWith(botNode(`Ошибка ${res.status}: ${await res.text()}`, null))
      return
    }
    const data = (await res.json()) as ClassifyResponse
    dialogHistory.push({ role: 'user', content: query })
    pending.replaceWith(botNode(data.answer, data))
    scrollDown()
  } catch (err) {
    pending.replaceWith(botNode(String(err), null))
  }
})

function appendUser(text: string): void {
  const div = document.createElement('div')
  div.className = 'msg user'
  div.textContent = text // textContent -> безопасно, без инъекции
  log.append(div)
  scrollDown()
}

function appendBot(text: string, data: ClassifyResponse | null): HTMLDivElement {
  const node = botNode(text, data)
  log.append(node)
  scrollDown()
  return node
}

function botNode(answer: string, data: ClassifyResponse | null): HTMLDivElement {
  const div = document.createElement('div')
  div.className = 'msg bot'

  const reply = document.createElement('div')
  reply.className = 'reply'
  reply.textContent = answer
  div.append(reply)

  if (data) div.append(debugNode(data))
  return div
}

function debugNode(data: ClassifyResponse): HTMLElement {
  const box = document.createElement('div')
  box.className = 'debug'

  const intents = data.intents
    .map(
      (i) =>
        `<li><b>${i.intent}</b>${i.target ? ` → <code>${esc(i.target)}</code>` : ''}` +
        ` <span class="conf">${Math.round(i.confidence * 100)}%</span></li>`,
    )
    .join('')

  const plan = data.plan
    .map(
      (p) =>
        `<li><b>${p.intent}</b>: ` +
        (p.command ? `<code>${esc(p.command)}</code>` : '<i>—</i>') +
        '</li>',
    )
    .join('')

  box.innerHTML =
    (data.needs_clarification ? '<p class="warn">⚠ нужно уточнение</p>' : '') +
    `<h4>интенты</h4><ul>${intents}</ul>` +
    `<h4>dry-run план</h4><ul>${plan}</ul>`
  return box
}

function scrollDown(): void {
  log.scrollTop = log.scrollHeight
}

// Защита от инъекции в DOM — наша ответственность (строки от модели идут в innerHTML).
function esc(value: string): string {
  const div = document.createElement('div')
  div.textContent = value
  return div.innerHTML
}

export {}
