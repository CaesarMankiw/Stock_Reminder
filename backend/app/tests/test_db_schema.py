from app.db.connection import connect
from app.db.schema import initialize_schema


def test_initialize_schema_creates_core_tables(tmp_path) -> None:
    database_path = tmp_path / "test.sqlite3"

    with connect(database_path) as connection:
        initialize_schema(connection)
        rows = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table'
              AND name IN ('assets', 'daily_prices', 'sync_jobs', 'alert_rules', 'alert_events')
            ORDER BY name
            """
        ).fetchall()

    assert [row["name"] for row in rows] == [
        "alert_events",
        "alert_rules",
        "assets",
        "daily_prices",
        "sync_jobs",
    ]
