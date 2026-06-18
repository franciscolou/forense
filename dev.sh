#!/usr/bin/env bash
# Sobe backend (FastAPI :8000) e frontend (Vite :5173) juntos.
# Assume dependências já instaladas (backend/.venv e frontend/node_modules).
# Ctrl+C encerra os dois.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
  echo ""
  echo "Encerrando..."
  # Mata o grupo de processos filhos (uvicorn + vite).
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# --- Backend ---
echo "→ Backend  em http://localhost:8000  (docs: /docs)"
(
  cd "$ROOT/backend"
  source .venv/bin/activate
  exec uvicorn app.main:app --reload --port 8000
) &

# --- Frontend ---
echo "→ Frontend em http://localhost:5173"
(
  cd "$ROOT/frontend"
  exec npm run dev
) &

wait
