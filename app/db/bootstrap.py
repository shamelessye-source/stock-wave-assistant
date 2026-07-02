from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_STATEMENTS = (
    """
    create table if not exists instruments (
        id integer primary key autoincrement,
        symbol text not null unique,
        name text not null,
        market text not null,
        industry text,
        enabled integer not null default 1,
        created_at text not null,
        updated_at text not null
    )
    """,
    """
    create table if not exists watchlist_items (
        id integer primary key autoincrement,
        instrument_id integer not null,
        group_name text not null default '核心观察',
        direction text,
        watch_reason text,
        core_logic text,
        risk_points_json text not null default '[]',
        status_label text not null default '正常跟踪',
        tags_json text not null default '[]',
        target_weight_pct real,
        max_weight_pct real,
        created_at text not null,
        updated_at text not null,
        foreign key (instrument_id) references instruments(id)
    )
    """,
    """
    create table if not exists app_metadata (
        key text primary key,
        value text not null,
        updated_at text not null
    )
    """,
    """
    create table if not exists trade_records (
        id integer primary key autoincrement,
        instrument_name text not null,
        instrument_code text not null default '',
        trade_date text not null,
        side text not null check(side in ('increase_position', 'decrease_position')),
        quantity text not null,
        price text not null,
        fee text not null default '0',
        note text not null default '',
        created_at text not null
    )
    """,
)


def initialize_database(database_path: str | Path) -> Path:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(path) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.execute(
            """
            insert into app_metadata(key, value, updated_at)
            values('schema_version', '1', ?)
            on conflict(key) do update set
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (now,),
        )
        connection.commit()
    return path
