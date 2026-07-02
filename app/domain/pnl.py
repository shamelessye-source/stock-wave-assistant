from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping


@dataclass(frozen=True)
class PnlTrade:
    instrument_name: str
    instrument_code: str
    side: str
    quantity: Decimal
    price: Decimal
    fee: Decimal


@dataclass(frozen=True)
class PnlItem:
    instrument_name: str
    instrument_code: str
    quantity: Decimal
    average_cost: Decimal
    cumulative_fee: Decimal
    realized_pnl: Decimal
    current_market_value: Decimal | None
    unrealized_pnl: Decimal | None
    total_pnl: Decimal
    status: str
    errors: list[str]


@dataclass(frozen=True)
class PnlSummary:
    items: list[PnlItem]


def calculate_pnl_summary(
    trades: list[PnlTrade],
    current_prices: Mapping[str, Decimal],
) -> PnlSummary:
    states: dict[tuple[str, str], _PnlState] = {}
    for trade in trades:
        key = (trade.instrument_name, trade.instrument_code)
        state = states.setdefault(
            key,
            _PnlState(
                instrument_name=trade.instrument_name,
                instrument_code=trade.instrument_code,
            ),
        )
        if trade.quantity <= 0:
            state.errors.append("quantity_must_be_positive")
            continue
        if trade.price < 0:
            state.errors.append("price_must_not_be_negative")
            continue
        if trade.fee < 0:
            state.errors.append("fee_must_not_be_negative")
            continue
        state.cumulative_fee += trade.fee
        if trade.side == "increase_position":
            _apply_increase(state, trade)
        elif trade.side == "decrease_position":
            _apply_decrease(state, trade)
        else:
            state.errors.append("unsupported_side")

    return PnlSummary(
        items=[
            _state_to_item(state, current_prices.get(state.instrument_name))
            for state in states.values()
        ]
    )


def _apply_increase(state: "_PnlState", trade: PnlTrade) -> None:
    previous_cost = state.quantity * state.average_cost
    added_cost = trade.quantity * trade.price + trade.fee
    state.quantity += trade.quantity
    if state.quantity > 0:
        state.average_cost = _money(previous_cost + added_cost) / state.quantity


def _apply_decrease(state: "_PnlState", trade: PnlTrade) -> None:
    if trade.quantity > state.quantity:
        state.errors.append("decrease_exceeds_position")
        return
    state.realized_pnl += trade.quantity * (trade.price - state.average_cost) - trade.fee
    state.quantity -= trade.quantity
    if state.quantity == 0:
        state.average_cost = Decimal("0")


def _state_to_item(state: "_PnlState", current_price: Decimal | None) -> PnlItem:
    errors = list(dict.fromkeys(state.errors))
    status = "ok"
    current_market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    if errors:
        status = "invalid_sequence"
    elif state.quantity > 0 and current_price is None:
        status = "price_missing"
    elif current_price is not None:
        current_market_value = _money(state.quantity * current_price)
        unrealized_pnl = _money(state.quantity * (current_price - state.average_cost))

    realized = _money(state.realized_pnl)
    total = realized + (unrealized_pnl or Decimal("0"))
    return PnlItem(
        instrument_name=state.instrument_name,
        instrument_code=state.instrument_code,
        quantity=_quantity(state.quantity),
        average_cost=_money(state.average_cost),
        cumulative_fee=_money(state.cumulative_fee),
        realized_pnl=realized,
        current_market_value=current_market_value,
        unrealized_pnl=unrealized_pnl,
        total_pnl=_money(total),
        status=status,
        errors=errors,
    )


@dataclass
class _PnlState:
    instrument_name: str
    instrument_code: str
    quantity: Decimal = Decimal("0")
    average_cost: Decimal = Decimal("0")
    cumulative_fee: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _quantity(value: Decimal) -> Decimal:
    return value.normalize()
