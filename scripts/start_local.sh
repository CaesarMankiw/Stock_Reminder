#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
DATABASE_PATH="${DATABASE_PATH:-${ROOT_DIR}/backend/data/stock_reminder.sqlite3}"
LOG_DIR="${LOG_DIR:-${ROOT_DIR}/logs}"
BACKEND_LOG="${BACKEND_LOG:-${LOG_DIR}/backend.log}"
FRONTEND_LOG="${FRONTEND_LOG:-${LOG_DIR}/frontend.log}"
STARTUP_CHECK="${STARTUP_CHECK:-0}"
STARTUP_SYNC="${STARTUP_SYNC:-0}"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [[ -n "${FRONTEND_PID}" ]]; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID}" ]]; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

port_in_use() {
  local port="$1"
  if ! command_exists lsof; then
    return 1
  fi
  lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
}

if ! command_exists python3; then
  echo "python3 is required. Install Python 3.11+ first."
  exit 1
fi

if ! command_exists npm; then
  echo "npm is required. Install Node.js 20+ first."
  exit 1
fi

if ! command_exists sqlite3; then
  echo "sqlite3 is required. Install SQLite first."
  exit 1
fi

if [[ ! -d "${ROOT_DIR}/backend/.venv" ]]; then
  echo "Backend virtual environment is missing."
  echo "Run: cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e \".[dev]\""
  exit 1
fi

if [[ ! -d "${ROOT_DIR}/frontend/node_modules" ]]; then
  echo "Frontend dependencies are missing."
  echo "Run: cd frontend && npm install"
  exit 1
fi

if [[ ! -f "${DATABASE_PATH}" ]]; then
  echo "SQLite database is missing: ${DATABASE_PATH}"
  echo "Run: cd backend && source .venv/bin/activate && python scripts/init_db.py && python scripts/seed_assets.py"
  echo "Then run historical sync if needed: python scripts/sync_history.py --years 5"
  exit 1
fi

if port_in_use "${BACKEND_PORT}"; then
  echo "Backend port ${BACKEND_PORT} is already in use."
  echo "Set BACKEND_PORT to another value or stop the existing process."
  exit 1
fi

if port_in_use "${FRONTEND_PORT}"; then
  echo "Frontend port ${FRONTEND_PORT} is already in use."
  echo "Set FRONTEND_PORT to another value or stop the existing process."
  exit 1
fi

mkdir -p "${LOG_DIR}"
touch "${BACKEND_LOG}" "${FRONTEND_LOG}"

if [[ "${STARTUP_CHECK}" == "1" ]]; then
  echo "Running startup check..."
  (
    cd "${ROOT_DIR}/backend"
    # shellcheck source=/dev/null
    source ".venv/bin/activate"
    python scripts/startup_check.py --database-path "${DATABASE_PATH}"
  )
fi

if [[ "${STARTUP_SYNC}" == "1" ]]; then
  echo "Running startup sync and alert check..."
  if ! DATABASE_PATH="${DATABASE_PATH}" "${ROOT_DIR}/scripts/run_daily_sync.sh" close; then
    echo "Startup close sync failed. Check ${LOG_DIR}/sync.log for details."
  fi
  if ! DATABASE_PATH="${DATABASE_PATH}" "${ROOT_DIR}/scripts/run_daily_sync.sh" alerts; then
    echo "Startup alert check failed. Check ${LOG_DIR}/sync.log for details."
  fi
fi

echo "Starting backend at http://${BACKEND_HOST}:${BACKEND_PORT}"
(
  cd "${ROOT_DIR}/backend"
  # shellcheck source=/dev/null
  source ".venv/bin/activate"
  export DATABASE_PATH
  uvicorn app.main:app --reload --host "${BACKEND_HOST}" --port "${BACKEND_PORT}"
) >> "${BACKEND_LOG}" 2>&1 &
BACKEND_PID="$!"

echo "Starting frontend at http://${FRONTEND_HOST}:${FRONTEND_PORT}"
(
  cd "${ROOT_DIR}/frontend"
  npm run dev -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}"
) >> "${FRONTEND_LOG}" 2>&1 &
FRONTEND_PID="$!"

echo "Backend health: http://${BACKEND_HOST}:${BACKEND_PORT}/health"
echo "Frontend app:   http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "Backend log:    ${BACKEND_LOG}"
echo "Frontend log:   ${FRONTEND_LOG}"
echo "Press Ctrl+C to stop both services."

while true; do
  if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
    exit_code=0
    wait "${BACKEND_PID}" || exit_code="$?"
    echo "Backend process exited. Check ${BACKEND_LOG} for details."
    exit "${exit_code}"
  fi
  if ! kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    exit_code=0
    wait "${FRONTEND_PID}" || exit_code="$?"
    echo "Frontend process exited. Check ${FRONTEND_LOG} for details."
    exit "${exit_code}"
  fi
  sleep 1
done
