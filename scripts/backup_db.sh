#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATABASE_PATH="${DATABASE_PATH:-${ROOT_DIR}/backend/data/stock_reminder.sqlite3}"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backend/data/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_PATH="${BACKUP_DIR}/stock_reminder_${TIMESTAMP}.sqlite3"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

check_integrity() {
  local path="$1"
  local result
  result="$(sqlite3 "${path}" "PRAGMA integrity_check;")"
  if [[ "${result}" != "ok" ]]; then
    echo "SQLite integrity check failed for ${path}: ${result}"
    exit 1
  fi
}

if ! command_exists sqlite3; then
  echo "sqlite3 is required. Install SQLite first."
  exit 1
fi

if [[ ! -f "${DATABASE_PATH}" ]]; then
  echo "Database file does not exist: ${DATABASE_PATH}"
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

check_integrity "${DATABASE_PATH}"
sqlite3 "${DATABASE_PATH}" ".backup '${BACKUP_PATH}'"
check_integrity "${BACKUP_PATH}"

SIZE_BYTES="$(wc -c < "${BACKUP_PATH}" | tr -d ' ')"
echo "Backup created: ${BACKUP_PATH}"
echo "Size bytes: ${SIZE_BYTES}"
