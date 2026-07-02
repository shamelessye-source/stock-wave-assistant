from pathlib import Path

from app.data.mock_market_provider import MockMarketProvider


def write_watchlist(path: Path) -> None:
    path.write_text(
        """
version: 1
stocks:
  - symbol: ""
    name: Alpha
    market: ""
    enabled: true
    group: 核心观察
    status: 正常跟踪
  - symbol: 000001.SZ
    name: Beta
    market: SZ
    enabled: true
    group: 核心观察
    status: 正常跟踪
""".strip(),
        encoding="utf-8",
    )


def test_mock_market_provider_generates_stable_daily_bars(tmp_path: Path) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    write_watchlist(watchlist_path)

    first = MockMarketProvider(watchlist_path=watchlist_path, seed=20260701).snapshot()
    second = MockMarketProvider(watchlist_path=watchlist_path, seed=20260701).snapshot()

    assert first == second
    assert len(first.items) == 2
    assert first.items[0].name == "Alpha"
    assert first.items[0].symbol == ""
    assert len(first.items[0].bars) >= 90
    latest = first.items[0].bars[-1]
    assert latest.trade_date
    assert latest.open > 0
    assert latest.high >= latest.low
    assert latest.close > 0
    assert latest.volume > 0
    assert latest.amount > 0
    assert latest.prev_close > 0


def test_mock_market_provider_can_generate_boundary_series(tmp_path: Path) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    write_watchlist(watchlist_path)
    provider = MockMarketProvider(watchlist_path=watchlist_path, seed=20260701)
    instrument = provider.load_instruments()[0]

    insufficient = provider.daily_bars_for(instrument, scenario="insufficient_history")
    zero_volume = provider.daily_bars_for(instrument, scenario="zero_volume")
    missing_price = provider.daily_bars_for(instrument, scenario="missing_price")

    assert len(insufficient) < 60
    assert zero_volume[-1].volume == 0
    assert zero_volume[-1].amount == 0
    assert missing_price[-1].close is None
