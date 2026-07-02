import sqlite3
from pathlib import Path

from app.db.bootstrap import initialize_database
from app.schemas.ledger import TradeRecordCreate
from app.services.ledger_service import create_trade_record, list_trade_records


def column_names(database_path: Path, table: str) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f"pragma table_info({table})").fetchall()
    return {row[1] for row in rows}


def test_initialize_database_creates_trade_records_table(tmp_path: Path) -> None:
    database_path = tmp_path / "ledger.db"

    initialize_database(database_path)

    assert {
        "id",
        "instrument_name",
        "instrument_code",
        "trade_date",
        "side",
        "quantity",
        "price",
        "fee",
        "note",
        "created_at",
    }.issubset(column_names(database_path, "trade_records"))


def test_create_and_list_trade_records(tmp_path: Path) -> None:
    database_path = tmp_path / "ledger.db"
    initialize_database(database_path)

    created = create_trade_record(
        database_path,
        TradeRecordCreate(
            instrument_name="中天科技",
            instrument_code="",
            trade_date="2026-06-30",
            side="increase_position",
            quantity="100",
            price="12.34",
            fee="1.23",
            note="manual fact",
        ),
    )
    records = list_trade_records(database_path)

    assert created["id"] == 1
    assert records == [
        {
            "id": 1,
            "instrument_name": "中天科技",
            "instrument_code": "",
            "trade_date": "2026-06-30",
            "side": "increase_position",
            "quantity": "100",
            "price": "12.34",
            "fee": "1.23",
            "note": "manual fact",
            "created_at": created["created_at"],
        }
    ]
