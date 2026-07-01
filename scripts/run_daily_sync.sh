#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${1:-}"
MARKET="${MARKET:-}"
TARGET_DATE="${TARGET_DATE:-}"
ASSET_ID="${ASSET_ID:-}"
DATABASE_PATH="${DATABASE_PATH:-${ROOT_DIR}/backend/data/stock_reminder.sqlite3}"
LOG_DIR="${LOG_DIR:-${ROOT_DIR}/logs}"
SYNC_LOG="${SYNC_LOG:-${LOG_DIR}/sync.log}"

usage() {
  echo "Usage: $0 <open|close|alerts|all>"
  echo "Optional env: MARKET=US TARGET_DATE=YYYY-MM-DD ASSET_ID=1 DATABASE_PATH=..."
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

run_backend_script() {
  local script="$1"
  shift
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] python ${script} $*" >> "${SYNC_LOG}"
  (
    cd "${ROOT_DIR}/backend"
    # shellcheck source=/dev/null
    source ".venv/bin/activate"
    export DATABASE_PATH
    python "${script}" "$@"
  ) >> "${SYNC_LOG}" 2>&1
}

run_open_sync() {
  local args=()
  if [[ -n "${MARKET}" ]]; then
    args+=(--market "${MARKET}")
  fi
  if [[ -n "${TARGET_DATE}" ]]; then
    args+=(--date "${TARGET_DATE}")
  fi
  if [[ -n "${ASSET_ID}" ]]; then
    args+=(--asset-id "${ASSET_ID}")
  fi
  if [[ "${#args[@]}" -gt 0 ]]; then
    run_backend_script scripts/sync_open.py "${args[@]}"
  else
    run_backend_script scripts/sync_open.py
  fi
}

run_close_sync() {
  local args=()
  if [[ -n "${MARKET}" ]]; then
    args+=(--market "${MARKET}")
  fi
  if [[ -n "${TARGET_DATE}" ]]; then
    args+=(--date "${TARGET_DATE}")
  fi
  if [[ -n "${ASSET_ID}" ]]; then
    args+=(--asset-id "${ASSET_ID}")
  fi
  if [[ "${#args[@]}" -gt 0 ]]; then
    run_backend_script scripts/sync_close.py "${args[@]}"
  else
    run_backend_script scripts/sync_close.py
  fi
}

run_alert_check() {
  local args=()
  if [[ -n "${ASSET_ID}" ]]; then
    args+=(--asset-id "${ASSET_ID}")
  fi
  if [[ "${#args[@]}" -gt 0 ]]; then
    run_backend_script scripts/check_alerts.py "${args[@]}"
  else
    run_backend_script scripts/check_alerts.py
  fi
}

if [[ -z "${ACTION}" ]]; then
  usage
  exit 1
fi

if ! command_exists python3; then
  echo "python3 is required. Install Python 3.11+ first."
  exit 1
fi

if [[ ! -d "${ROOT_DIR}/backend/.venv" ]]; then
  echo "Backend virtual environment is missing."
  echo "Run: cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e \".[dev]\""
  exit 1
fi

mkdir -p "${LOG_DIR}"
touch "${SYNC_LOG}"

case "${ACTION}" in
  open)
    run_open_sync
    ;;
  close)
    run_close_sync
    ;;
  alerts)
    run_alert_check
    ;;
  all)
    run_close_sync
    run_open_sync
    run_alert_check
    ;;
  *)
    usage
    exit 1
    ;;
esac

echo "Completed action: ${ACTION}"
echo "Sync log: ${SYNC_LOG}"
