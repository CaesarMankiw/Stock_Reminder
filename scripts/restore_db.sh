#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATABASE_PATH="${DATABASE_PATH:-${ROOT_DIR}/backend/data/stock_reminder.sqlite3}"
BACKUP_PATH="${1:-}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
SAFETY_COPY="${DATABASE_PATH%.sqlite3}_before_restore_${TIMESTAMP}.sqlite3"

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

if [[ -z "${BACKUP_PATH}" ]]; then
  echo "Usage: $0 <backup-sqlite3-path>"
  exit 1
fi

if [[ ! -f "${BACKUP_PATH}" ]]; then
  echo "Backup file does not exist: ${BACKUP_PATH}"
  exit 1
fi

check_integrity "${BACKUP_PATH}"
mkdir -p "$(dirname "${DATABASE_PATH}")"

if [[ -f "${DATABASE_PATH}" ]]; then
  mv "${DATABASE_PATH}" "${SAFETY_COPY}"
  echo "Current database moved to: ${SAFETY_COPY}"
fi

if sqlite3 "${BACKUP_PATH}" ".backup '${DATABASE_PATH}'"; then
  check_integrity "${DATABASE_PATH}"
  echo "Database restored from: ${BACKUP_PATH}"
  echo "Restored database: ${DATABASE_PATH}"
else
  echo "Restore failed."
  rm -f "${DATABASE_PATH}"
  if [[ -f "${SAFETY_COPY}" ]]; then
    mv "${SAFETY_COPY}" "${DATABASE_PATH}"
    echo "Original database restored from safety copy."
  fi
  exit 1
fi
