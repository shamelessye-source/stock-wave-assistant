from pathlib import Path

from app.core.config import load_settings
from app.data.akshare_market_provider import AkShareMarketProvider, AkShareUnavailable
from app.data.market_provider import create_market_provider
from app.data.mock_market_provider import MockMarketProvider


class FakeAkShareClient:
    def __init__(self, rows_by_symbol: dict[str, list[dict[str, object]]]) -> None:
        self.rows_by_symbol = rows_by_symbol
        self.calls: list[str] = []

    def stock_zh_a_hist(self, symbol: str) -> list[dict[str, object]]:
        self.calls.append(symbol)
        return self.rows_by_symbol.get(symbol, [])


class FailingAkShareClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def stock_zh_a_hist(self, symbol: str) -> list[dict[str, object]]:
        self.calls.append(symbol)
        raise RuntimeError("network down")


class MissingAkShareClient:
    def stock_zh_a_hist(self, symbol: str) -> list[dict[str, object]]:
        raise AkShareUnavailable("akshare_not_installed")


def test_akshare_provider_standardizes_daily_rows(tmp_path: Path) -> None:
    provider = AkShareMarketProvider(
        watchlist_path=write_watchlist(tmp_path, symbol="000001.SZ"),
        cache_dir=tmp_path / "cache",
        client=FakeAkShareClient(
            {
                "000001": [
                    {
                        "日期": "2026-06-28",
                        "开盘": "10.0",
                        "最高": "10.8",
                        "最低": "9.9",
                        "收盘": "10.5",
                        "成交量": "1000",
                        "成交额": "10500",
                    },
                    {
                        "日期": "2026-06-29",
                        "开盘": "10.6",
                        "最高": "11.0",
                        "最低": "10.4",
                        "收盘": "10.8",
                        "成交量": "1200",
                        "成交额": "12960",
                    },
                ]
            }
        ),
    )

    snapshot = provider.snapshot()

    assert snapshot.provider == "akshare"
    assert snapshot.bar_count == 2
    series = snapshot.items[0]
    assert series.symbol == "000001.SZ"
    assert series.data_status == "ok"
    assert series.bars[0].trade_date == "2026-06-28"
    assert series.bars[0].open == 10.0
    assert series.bars[0].high == 10.8
    assert series.bars[0].low == 9.9
    assert series.bars[0].close == 10.5
    assert series.bars[0].volume == 1000
    assert series.bars[0].amount == 10500.0
    assert series.bars[0].prev_close == 10.5
    assert series.bars[1].prev_close == 10.5


def test_akshare_provider_reports_missing_code_without_guessing(tmp_path: Path) -> None:
    client = FailingAkShareClient()
    provider = AkShareMarketProvider(
        watchlist_path=write_watchlist(tmp_path, symbol=""),
        cache_dir=tmp_path / "cache",
        client=client,
    )

    snapshot = provider.snapshot()

    assert client.calls == []
    assert snapshot.items[0].data_status == "code_missing"
    assert snapshot.items[0].bars == []
    assert snapshot.items[0].degradation_reasons == ["symbol_missing:Alpha"]


def test_akshare_provider_reports_empty_data(tmp_path: Path) -> None:
    provider = AkShareMarketProvider(
        watchlist_path=write_watchlist(tmp_path, symbol="000001.SZ"),
        cache_dir=tmp_path / "cache",
        client=FakeAkShareClient({"000001": []}),
    )

    snapshot = provider.snapshot()

    assert snapshot.items[0].data_status == "data_empty"
    assert snapshot.items[0].degradation_reasons == ["akshare_empty:000001.SZ"]


def test_akshare_provider_reports_field_mismatch(tmp_path: Path) -> None:
    provider = AkShareMarketProvider(
        watchlist_path=write_watchlist(tmp_path, symbol="000001.SZ"),
        cache_dir=tmp_path / "cache",
        client=FakeAkShareClient({"000001": [{"unexpected": "value"}]}),
    )

    snapshot = provider.snapshot()

    assert snapshot.items[0].data_status == "field_mismatch"
    assert snapshot.items[0].degradation_reasons == [
        "akshare_field_mismatch:missing_field:日期/trade_date/date"
    ]


def test_akshare_provider_reports_network_error_without_cache(tmp_path: Path) -> None:
    provider = AkShareMarketProvider(
        watchlist_path=write_watchlist(tmp_path, symbol="000001.SZ"),
        cache_dir=tmp_path / "cache",
        client=FailingAkShareClient(),
    )

    snapshot = provider.snapshot()

    assert snapshot.items[0].data_status == "source_unavailable"
    assert snapshot.items[0].degradation_reasons == ["akshare_error:network down"]


def test_akshare_provider_reports_missing_package(tmp_path: Path) -> None:
    provider = AkShareMarketProvider(
        watchlist_path=write_watchlist(tmp_path, symbol="000001.SZ"),
        cache_dir=tmp_path / "cache",
        client=MissingAkShareClient(),
    )

    snapshot = provider.snapshot()

    assert snapshot.items[0].data_status == "source_unavailable"
    assert snapshot.items[0].degradation_reasons == [
        "akshare_error:akshare_not_installed"
    ]


def test_akshare_provider_uses_cache_before_network(tmp_path: Path) -> None:
    watchlist_path = write_watchlist(tmp_path, symbol="000001.SZ")
    cache_dir = tmp_path / "cache"
    first_client = FakeAkShareClient(
        {
            "000001": [
                {
                    "日期": "2026-06-29",
                    "开盘": "10.6",
                    "最高": "11.0",
                    "最低": "10.4",
                    "收盘": "10.8",
                    "成交量": "1200",
                    "成交额": "12960",
                }
            ]
        }
    )
    first = AkShareMarketProvider(
        watchlist_path=watchlist_path,
        cache_dir=cache_dir,
        client=first_client,
    ).snapshot()
    failing_client = FailingAkShareClient()

    second = AkShareMarketProvider(
        watchlist_path=watchlist_path,
        cache_dir=cache_dir,
        client=failing_client,
    ).snapshot()

    assert first.items[0].bars == second.items[0].bars
    assert second.items[0].data_status == "ok"
    assert second.items[0].source == "cache"
    assert second.items[0].cache_status == "hit"
    assert second.items[0].degradation_reasons == []
    assert failing_client.calls == []


def test_market_provider_factory_keeps_mock_default(tmp_path: Path) -> None:
    mock_settings = load_settings(config_dir=tmp_path, env={"MARKET_PROVIDER": "mock"})
    akshare_settings = load_settings(
        config_dir=tmp_path,
        env={
            "MARKET_PROVIDER": "akshare",
            "CACHE_DIR": str(tmp_path / "cache"),
        },
    )

    assert isinstance(create_market_provider(mock_settings), MockMarketProvider)
    assert isinstance(create_market_provider(akshare_settings), AkShareMarketProvider)


def write_watchlist(tmp_path: Path, symbol: str) -> Path:
    path = tmp_path / "watchlist.yaml"
    path.write_text(
        f"""
version: 1
stocks:
  - symbol: "{symbol}"
    name: Alpha
    market: ""
    enabled: true
    group: 核心观察
    status: 正常跟踪
""".strip(),
        encoding="utf-8",
    )
    return path
