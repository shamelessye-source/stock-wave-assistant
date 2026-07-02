from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.db.bootstrap import initialize_database
from app.schemas.ledger import TradeRecordCreate


def create_trade_record(
    database_path: str | Path,
    payload: TradeRecordCreate,
) -> dict[str, Any]:
    initialize_database(database_path)
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            """
            insert into trade_records(
                instrument_name,
                instrument_code,
                trade_date,
                side,
                quantity,
                price,
                fee,
                note,
                created_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.instrument_name,
                payload.instrument_code,
                payload.trade_date,
                payload.side,
                _decimal_text(payload.quantity),
                _decimal_text(payload.price),
                _decimal_text(payload.fee),
                payload.note,
                created_at,
            ),
        )
        connection.commit()
        record_id = int(cursor.lastrowid)
    return get_trade_record(database_path, record_id)


def get_trade_record(database_path: str | Path, record_id: int) -> dict[str, Any]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            select
                id,
                instrument_name,
                instrument_code,
                trade_date,
                side,
                quantity,
                price,
                fee,
                note,
                created_at
            from trade_records
            where id = ?
            """,
            (record_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"trade record not found: {record_id}")
    return dict(row)


def list_trade_records(database_path: str | Path) -> list[dict[str, Any]]:
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            select
                id,
                instrument_name,
                instrument_code,
                trade_date,
                side,
                quantity,
                price,
                fee,
                note,
                created_at
            from trade_records
            order by trade_date asc, id asc
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _decimal_text(value: object) -> str:
    return format(value, "f")
