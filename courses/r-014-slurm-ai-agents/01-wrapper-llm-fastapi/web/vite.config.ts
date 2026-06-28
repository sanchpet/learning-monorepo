import { defineConfig } from 'vite'

// Dev-прокси — так мы НЕ настраиваем CORS на бэкенде.
// Браузер бьёт в тот же origin (vite, :5173), а vite пересылает /api/* на
// FastAPI (:8000). Для браузера это один источник — CORS не возникает.
// В проде SPA собирается в dist/ и раздаётся тем же FastAPI (тоже один origin),
// поэтому CORS не нужен нигде — мы его обошли архитектурно, а не заплаткой.
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
