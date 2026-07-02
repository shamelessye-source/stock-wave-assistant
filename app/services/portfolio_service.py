from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from app.core.config import AppSettings, load_watchlist_config
from app.data.mock_market_provider import MockMarketProvider
from app.domain.indicators import build_indicator_snapshot
from app.domain.pnl import PnlSummary, PnlTrade, calculate_pnl_summary
from app.domain.report_builder import PrecloseReport, build_preclose_report
from app.domain.risk import RiskSummary, calculate_risk_summary
from app.domain.trading_calendar import evaluate_market_session
from app.domain.wave_state import WaveStateItem, build_wave_states
from app.schemas.indicators import IndicatorSnapshot
from app.services.ledger_service import list_trade_records


def build_current_pnl_summary(settings: AppSettings) -> PnlSummary:
    records = list_trade_records(settings.database_path)
    return calculate_pnl_summary(
        [_record_to_pnl_trade(record) for record in records],
        current_prices=mock_current_prices(settings),
    )


def build_current_risk_summary(settings: AppSettings) -> RiskSummary:
    return calculate_risk_summary(
        pnl_items=build_current_pnl_summary(settings).items,
        watchlist_config=load_watchlist_config(settings.config_dir / "watchlist.yaml"),
        preferences_config=_read_optional_yaml(settings.config_dir / "preferences.yaml"),
        factor_config=_read_optional_yaml(settings.config_dir / "factors.yaml"),
    )


def build_current_wave_states(settings: AppSettings) -> list[WaveStateItem]:
    pnl_summary = build_current_pnl_summary(settings)
    risk_summary = calculate_risk_summary(
        pnl_items=pnl_summary.items,
        watchlist_config=load_watchlist_config(settings.config_dir / "watchlist.yaml"),
        preferences_config=_read_optional_yaml(settings.config_dir / "preferences.yaml"),
        factor_config=_read_optional_yaml(settings.config_dir / "factors.yaml"),
    )
    return build_wave_states(
        indicator_snapshots=build_indicator_snapshots(settings),
        risk_summary=risk_summary,
        pnl_items=pnl_summary.items,
    )


def build_current_preclose_report(
    settings: AppSettings,
    as_of: datetime,
) -> PrecloseReport:
    preferences_config = _read_optional_yaml(settings.config_dir / "preferences.yaml")
    factor_config = _read_optional_yaml(settings.config_dir / "factors.yaml")
    watchlist_config = load_watchlist_config(settings.config_dir / "watchlist.yaml")
    indicator_snapshots = build_indicator_snapshots(settings)
    pnl_summary = build_current_pnl_summary(settings)
    risk_summary = calculate_risk_summary(
        pnl_items=pnl_summary.items,
        watchlist_config=watchlist_config,
        preferences_config=preferences_config,
        factor_config=factor_config,
    )
    wave_states = build_wave_states(
        indicator_snapshots=indicator_snapshots,
        risk_summary=risk_summary,
        pnl_items=pnl_summary.items,
    )
    return build_preclose_report(
        indicator_snapshots=indicator_snapshots,
        risk_summary=risk_summary,
        wave_states=wave_states,
        pnl_summary=pnl_summary,
        market_session_status=evaluate_market_session(as_of, preferences_config),
        generated_at=as_of,
    )


def build_indicator_snapshots(settings: AppSettings) -> list[IndicatorSnapshot]:
    provider = MockMarketProvider(settings.config_dir / "watchlist.yaml")
    return [
        build_indicator_snapshot(instrument, provider.daily_bars_for(instrument))
        for instrument in provider.load_instruments()
    ]


def mock_current_prices(settings: AppSettings) -> dict[str, Decimal]:
    provider = MockMarketProvider(settings.config_dir / "watchlist.yaml")
    prices: dict[str, Decimal] = {}
    for item in provider.snapshot().items:
        latest_close = item.bars[-1].close
        if latest_close is not None:
            prices[item.name] = Decimal(str(latest_close))
    return prices


def decimal_dataclass_to_response(value: object) -> dict[str, Any]:
    return _decimal_to_text(asdict(value))


def _record_to_pnl_trade(record: dict[str, object]) -> PnlTrade:
    return PnlTrade(
        instrument_name=str(record["instrument_name"]),
        instrument_code=str(record["instrument_code"]),
        side=str(record["side"]),
        quantity=Decimal(str(record["quantity"])),
        price=Decimal(str(record["price"])),
        fee=Decimal(str(record["fee"])),
    )


def _read_optional_yaml(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        return {}
    return loaded


def _decimal_to_text(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {key: _decimal_to_text(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decimal_to_text(item) for item in value]
    return value
