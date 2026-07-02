from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


Side = Literal["increase_position", "decrease_position"]


class TradeRecordCreate(BaseModel):
    instrument_name: str = Field(min_length=1)
    instrument_code: str = ""
    trade_date: str = Field(min_length=1)
    side: Side
    quantity: Decimal = Field(gt=Decimal("0"))
    price: Decimal = Field(ge=Decimal("0"))
    fee: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    note: str = ""

    @field_validator("instrument_name", "trade_date")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field is required")
        return stripped

    @field_validator("instrument_code", "note")
    @classmethod
    def optional_text_should_be_trimmed(cls, value: str) -> str:
        return value.strip()


class TradeRecordResponse(BaseModel):
    id: int
    instrument_name: str
    instrument_code: str
    trade_date: str
    side: Side
    quantity: str
    price: str
    fee: str
    note: str
    created_at: str


class TradeRecordsResponse(BaseModel):
    items: list[TradeRecordResponse]


class LedgerSummaryItem(BaseModel):
    instrument_name: str
    instrument_code: str
    quantity: str
    average_cost: str
    cumulative_fee: str
    realized_pnl: str
    current_market_value: str | None
    unrealized_pnl: str | None
    total_pnl: str
    status: str
    errors: list[str]


class LedgerSummaryResponse(BaseModel):
    items: list[LedgerSummaryItem]
