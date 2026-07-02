from decimal import Decimal

from app.domain.pnl import PnlTrade, calculate_pnl_summary


def test_calculate_pnl_uses_moving_average_cost() -> None:
    summary = calculate_pnl_summary(
        [
            PnlTrade("Alpha", "", "increase_position", Decimal("10"), Decimal("10"), Decimal("1")),
            PnlTrade("Alpha", "", "increase_position", Decimal("10"), Decimal("20"), Decimal("1")),
            PnlTrade("Alpha", "", "decrease_position", Decimal("5"), Decimal("30"), Decimal("1")),
        ],
        current_prices={"Alpha": Decimal("25")},
    )

    alpha = summary.items[0]
    assert alpha.status == "ok"
    assert alpha.quantity == Decimal("15")
    assert alpha.average_cost == Decimal("15.10")
    assert alpha.cumulative_fee == Decimal("3")
    assert alpha.realized_pnl == Decimal("73.50")
    assert alpha.current_market_value == Decimal("375")
    assert alpha.unrealized_pnl == Decimal("148.50")
    assert alpha.total_pnl == Decimal("222.00")


def test_calculate_pnl_reports_decrease_before_position_error() -> None:
    summary = calculate_pnl_summary(
        [
            PnlTrade("Alpha", "", "decrease_position", Decimal("5"), Decimal("12"), Decimal("0")),
        ],
        current_prices={"Alpha": Decimal("12")},
    )

    alpha = summary.items[0]
    assert alpha.status == "invalid_sequence"
    assert "decrease_exceeds_position" in alpha.errors


def test_calculate_pnl_degrades_when_current_price_is_missing() -> None:
    summary = calculate_pnl_summary(
        [
            PnlTrade("Alpha", "", "increase_position", Decimal("10"), Decimal("12"), Decimal("0")),
        ],
        current_prices={},
    )

    alpha = summary.items[0]
    assert alpha.status == "price_missing"
    assert alpha.current_market_value is None
    assert alpha.unrealized_pnl is None
    assert alpha.total_pnl == Decimal("0")
