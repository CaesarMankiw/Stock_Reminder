from __future__ import annotations

from app.db.connection import connect, get_database_path
from app.db.schema import initialize_schema


def main() -> int:
    with connect() as connection:
        initialize_schema(connection)
    print(f"Initialized SQLite database: {get_database_path()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

