from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.config import get_settings


def get_database_path(database_path: str | Path | None = None) -> Path:
    path = Path(database_path or get_settings().database_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def connect(database_path: str | Path | None = None) -> sqlite3.Connection:
    path = get_database_path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

