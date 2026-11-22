#!/usr/bin/env bash
# Start the orchestrator and the dashboard. The cluster is the built-in simulator.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r orchestrator/requirements.txt -r mcp-server/requirements.txt
fi

if [[ ! -d chat-ui/node_modules ]]; then
  npm install --prefix chat-ui
fi

export INFRAGPT_K8S_MODE="${INFRAGPT_K8S_MODE:-mock}"
export ORCHESTRATOR_PORT="${ORCHESTRATOR_PORT:-8888}"

.venv/bin/python orchestrator/app.py &
BACK_PID=$!
npm --prefix chat-ui run dev &
UI_PID=$!

cleanup() {
  kill "$BACK_PID" "$UI_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
wait
