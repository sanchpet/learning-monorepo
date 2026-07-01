#!/usr/bin/env bash
# Start the LiteLLM gateway on :4000, loading .env for OPENROUTER_API_KEY +
# LITELLM_MASTER_KEY. Run from anywhere; paths resolve relative to the module root.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "no .env — copy .env.example and fill OPENROUTER_API_KEY + LITELLM_MASTER_KEY" >&2
  exit 1
fi

set -a; source .env; set +a   # export every var from .env into the proxy's environment
exec uv run litellm --config litellm/config.yaml --port 4000
