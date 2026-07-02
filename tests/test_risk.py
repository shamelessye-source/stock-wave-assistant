from decimal import Decimal

from app.domain.pnl import PnlItem
from app.domain.risk import calculate_risk_summary


def pnl_item(
    name: str,
    market_value: str,
    unrealized: str,
    realized: str,
    total: str,
) -> PnlItem:
    return PnlItem(
        instrument_name=name,
        instrument_code="",
        quantity=Decimal("100"),
        average_cost=Decimal("10"),
        cumulative_fee=Decimal("1"),
        realized_pnl=Decimal(realized),
        current_market_value=Decimal(market_value),
        unrealized_pnl=Decimal(unrealized),
        total_pnl=Decimal(total),
        status="ok",
        errors=[],
    )


def watchlist_config() -> dict[str, object]:
    return {
        "stocks": [
            {
                "name": "Alpha",
                "symbol": "",
                "group": "核心观察",
                "direction": "半导体封测",
                "enabled": True,
            },
            {
                "name": "Beta",
                "symbol": "",
                "group": "核心观察",
                "direction": "半导体封测",
                "enabled": True,
            },
        ]
    }


def test_calculate_risk_summary_uses_internal_market_value_weights() -> None:
    summary = calculate_risk_summary(
        pnl_items=[
            pnl_item("Alpha", "700", "70", "5", "75"),
            pnl_item("Beta", "300", "-10", "0", "-10"),
        ],
        watchlist_config=watchlist_config(),
        preferences_config={},
        factor_config={
            "thresholds": {
                "max_single_position_pct": 60.0,
                "max_direction_position_pct": 80.0,
            }
        },
    )

    assert summary.total_market_value == Decimal("1000.00")
    assert summary.floating_pnl == Decimal("60.00")
    assert summary.realized_pnl == Decimal("5.00")
    assert summary.total_pnl == Decimal("65.00")
    assert summary.max_single_position.instrument_name == "Alpha"
    assert summary.max_single_position.weight_pct == Decimal("70.00")
    assert summary.max_single_position.risk_status == "high_concentration"
    assert "capital_base_missing" in summary.degradation_reasons


def test_calculate_risk_summary_reports_direction_concentration() -> None:
    summary = calculate_risk_summary(
        pnl_items=[
            pnl_item("Alpha", "700", "70", "0", "70"),
            pnl_item("Beta", "300", "30", "0", "30"),
        ],
        watchlist_config=watchlist_config(),
        preferences_config={},
        factor_config={
            "thresholds": {
                "max_single_position_pct": 90.0,
                "max_direction_position_pct": 80.0,
            }
        },
    )

    assert summary.direction_concentration[0].name == "半导体封测"
    assert summary.direction_concentration[0].weight_pct == Decimal("100.00")
    assert summary.direction_concentration[0].risk_status == "high_concentration"


def test_calculate_risk_summary_degrades_when_market_value_is_missing() -> None:
    missing_price_item = pnl_item("Alpha", "0", "0", "0", "0")
    missing_price_item = PnlItem(
        **{
            **missing_price_item.__dict__,
            "current_market_value": None,
            "unrealized_pnl": None,
            "status": "price_missing",
            "errors": [],
        }
    )

    summary = calculate_risk_summary(
        pnl_items=[missing_price_item],
        watchlist_config=watchlist_config(),
        preferences_config={},
        factor_config={"thresholds": {}},
    )

    assert summary.data_status == "data_incomplete"
    assert "price_missing:Alpha" in summary.degradation_reasons
