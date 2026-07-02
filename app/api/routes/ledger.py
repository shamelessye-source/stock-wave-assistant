from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal

from fastapi import APIRouter

from app.core.config import load_settings
from app.data.market_provider import create_market_provider
from app.domain.pnl import PnlTrade, calculate_pnl_summary
from app.schemas.ledger import (
    LedgerSummaryResponse,
    TradeRecordCreate,
    TradeRecordResponse,
    TradeRecordsResponse,
)
from app.services.ledger_service import create_trade_record, list_trade_records


router = APIRouter()


@router.get("/api/ledger/trades", response_model=TradeRecordsResponse)
def ledger_trades() -> dict[str, object]:
    settings = load_settings()
    return {
        "items": list_trade_records(settings.database_path),
    }


@router.post("/api/ledger/trades", response_model=TradeRecordResponse)
def ledger_trade_create(payload: TradeRecordCreate) -> dict[str, object]:
    settings = load_settings()
    return create_trade_record(settings.database_path, payload)


@router.get("/api/ledger/summary", response_model=LedgerSummaryResponse)
def ledger_summary() -> dict[str, object]:
    settings = load_settings()
    records = list_trade_records(settings.database_path)
    summary = calculate_pnl_summary(
        [_record_to_pnl_trade(record) for record in records],
        current_prices=_mock_current_prices(),
    )
    return {
        "items": [_pnl_item_to_response(item) for item in summary.items],
    }


def _record_to_pnl_trade(record: dict[str, object]) -> PnlTrade:
    return PnlTrade(
        instrument_name=str(record["instrument_name"]),
        instrument_code=str(record["instrument_code"]),
        side=str(record["side"]),
        quantity=Decimal(str(record["quantity"])),
        price=Decimal(str(record["price"])),
        fee=Decimal(str(record["fee"])),
    )


def _mock_current_prices() -> dict[str, Decimal]:
    provider = create_market_provider(load_settings())
    prices: dict[str, Decimal] = {}
    for item in provider.snapshot().items:
        if not item.bars:
            continue
        latest_close = item.bars[-1].close
        if latest_close is not None:
            prices[item.name] = Decimal(str(latest_close))
    return prices


def _pnl_item_to_response(item: object) -> dict[str, object]:
    raw = asdict(item)
    for key in (
        "quantity",
        "average_cost",
        "cumulative_fee",
        "realized_pnl",
        "current_market_value",
        "unrealized_pnl",
        "total_pnl",
    ):
        if raw[key] is not None:
            raw[key] = format(raw[key], "f")
    return raw
