import sqlite3
from pathlib import Path

from app.db.bootstrap import initialize_database


def table_names(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "select name from sqlite_master where type = 'table'"
        ).fetchall()
    return {row[0] for row in rows}


def test_initialize_database_creates_minimal_task_2_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "task2.db"

    initialize_database(database_path)

    assert database_path.exists()
    assert {
        "instruments",
        "watchlist_items",
        "app_metadata",
    }.issubset(table_names(database_path))


def test_initialize_database_does_not_create_future_domain_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "task2.db"

    initialize_database(database_path)

    assert "ledger_entries" not in table_names(database_path)
    assert "daily_bars" not in table_names(database_path)
    assert "reports" not in table_names(database_path)
