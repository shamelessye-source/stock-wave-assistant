from app.data.mock_market_provider import MockInstrument, MockMarketProvider
from app.domain.indicators import build_indicator_snapshot, momentum_pct, moving_average


def test_indicator_helpers_compute_expected_values() -> None:
    values = [float(number) for number in range(1, 22)]

    assert moving_average(values, 20) == 11.5
    assert round(momentum_pct(values, 5), 4) == round((21 / 16 - 1) * 100, 4)
    assert round(momentum_pct(values, 10), 4) == round((21 / 11 - 1) * 100, 4)
    assert round(momentum_pct(values, 20), 4) == round((21 / 1 - 1) * 100, 4)


def test_indicator_snapshot_contains_core_fields_for_normal_mock_data() -> None:
    provider = MockMarketProvider(seed=20260701)
    instrument = MockInstrument(symbol="", name="Alpha", market="")
    bars = provider.daily_bars_for(instrument)

    snapshot = build_indicator_snapshot(instrument, bars)

    assert snapshot.name == "Alpha"
    assert snapshot.symbol == ""
    assert snapshot.latest_trade_date == bars[-1].trade_date
    assert snapshot.latest_close == bars[-1].close
    assert snapshot.data_status == "ok"
    assert snapshot.degradation_reasons == []
    assert snapshot.indicators.ma20 is not None
    assert snapshot.indicators.ma60 is not None
    assert snapshot.indicators.momentum_5d_pct is not None
    assert snapshot.indicators.momentum_10d_pct is not None
    assert snapshot.indicators.momentum_20d_pct is not None
    assert snapshot.indicators.max_drawdown_pct is not None
    assert snapshot.indicators.atr_pct is not None
    assert snapshot.indicators.volume_ratio is not None


def test_indicator_snapshot_degrades_when_history_is_insufficient() -> None:
    provider = MockMarketProvider(seed=20260701)
    instrument = MockInstrument(symbol="", name="Alpha", market="")
    bars = provider.daily_bars_for(instrument, scenario="insufficient_history")

    snapshot = build_indicator_snapshot(instrument, bars)

    assert snapshot.data_status == "data_insufficient"
    assert "requires_at_least_60_bars" in snapshot.degradation_reasons
    assert snapshot.indicators.ma60 is None


def test_indicator_snapshot_degrades_when_latest_volume_is_zero() -> None:
    provider = MockMarketProvider(seed=20260701)
    instrument = MockInstrument(symbol="", name="Alpha", market="")
    bars = provider.daily_bars_for(instrument, scenario="zero_volume")

    snapshot = build_indicator_snapshot(instrument, bars)

    assert snapshot.data_status == "volume_missing"
    assert "latest_volume_missing_or_zero" in snapshot.degradation_reasons
    assert snapshot.indicators.volume_ratio is None


def test_indicator_snapshot_degrades_when_latest_price_is_missing() -> None:
    provider = MockMarketProvider(seed=20260701)
    instrument = MockInstrument(symbol="", name="Alpha", market="")
    bars = provider.daily_bars_for(instrument, scenario="missing_price")

    snapshot = build_indicator_snapshot(instrument, bars)

    assert snapshot.data_status == "price_missing"
    assert "latest_price_missing" in snapshot.degradation_reasons
    assert snapshot.latest_close is None
