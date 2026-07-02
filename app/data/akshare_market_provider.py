from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from app.core.config import load_watchlist_config
from app.schemas.market import DailyBar, MarketSeries, MarketSnapshot


class AkShareClient(Protocol):
    def stock_zh_a_hist(self, symbol: str) -> object:
        """Return raw AkShare daily history rows for a normalized symbol."""


@dataclass(frozen=True)
class AkShareInstrument:
    symbol: str
    name: str
    market: str


class AkShareUnavailable(RuntimeError):
    """Raised when the real AkShare package is not installed or unavailable."""


class AkShareImportClient:
    def stock_zh_a_hist(self, symbol: str) -> object:
        try:
            import akshare as ak  # type: ignore[import-not-found]
        except ImportError as exc:
            raise AkShareUnavailable("akshare_not_installed") from exc
        return ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="")


class AkShareMarketProvider:
    """AkShare daily-bar provider with local JSON cache and clear degradation."""

    def __init__(
        self,
        watchlist_path: str | Path = "config/watchlist.yaml",
        cache_dir: str | Path = "data/cache",
        client: AkShareClient | None = None,
    ) -> None:
        self.watchlist_path = Path(watchlist_path)
        self.cache_dir = Path(cache_dir)
        self.client = client or AkShareImportClient()

    def load_instruments(self) -> list[AkShareInstrument]:
        config = load_watchlist_config(self.watchlist_path)
        instruments: list[AkShareInstrument] = []
        for stock in config["stocks"]:
            if stock.get("enabled", True) is False:
                continue
            instruments.append(
                AkShareInstrument(
                    symbol=str(stock.get("symbol") or "").strip(),
                    name=str(stock.get("name") or "").strip(),
                    market=str(stock.get("market") or "").strip(),
                )
            )
        return instruments

    def snapshot(self) -> MarketSnapshot:
        items = [self._series_for(instrument) for instrument in self.load_instruments()]
        reasons = [
            reason
            for item in items
            if item.data_status != "ok"
            for reason in item.degradation_reasons
        ]
        return MarketSnapshot(
            provider="akshare",
            bar_count=max((len(item.bars) for item in items), default=0),
            items=items,
            data_status="ok" if not reasons else "partial",
            degradation_reasons=reasons,
        )

    def daily_bars_for(self, instrument: AkShareInstrument) -> list[DailyBar]:
        return self._series_for(instrument).bars

    def _series_for(self, instrument: AkShareInstrument) -> MarketSeries:
        if not instrument.symbol:
            return MarketSeries(
                name=instrument.name,
                symbol=instrument.symbol,
                market=instrument.market,
                bars=[],
                data_status="code_missing",
                degradation_reasons=[f"symbol_missing:{instrument.name}"],
                source="config",
            )

        normalized_symbol = _normalize_symbol(instrument.symbol)
        cache_path = self._cache_path(normalized_symbol)
        cache_status = "miss"
        cache_read_error: str | None = None
        try:
            cached = self._read_cache(cache_path)
        except (json.JSONDecodeError, TypeError, ValueError, OSError) as exc:
            cached = None
            cache_status = "read_error"
            cache_read_error = _cache_read_error_reason(exc)
        if cached is not None:
            return MarketSeries(
                name=instrument.name,
                symbol=instrument.symbol,
                market=instrument.market,
                bars=cached,
                data_status="ok",
                source="cache",
                cache_status="hit",
            )

        try:
            rows = _raw_rows(self.client.stock_zh_a_hist(normalized_symbol))
        except Exception as exc:  # AkShare and network errors vary by environment.
            return MarketSeries(
                name=instrument.name,
                symbol=instrument.symbol,
                market=instrument.market,
                bars=[],
                data_status="source_unavailable",
                degradation_reasons=_with_cache_error(
                    cache_read_error,
                    f"akshare_error:{exc}",
                ),
                source="akshare",
                cache_status=cache_status,
            )

        if not rows:
            return MarketSeries(
                name=instrument.name,
                symbol=instrument.symbol,
                market=instrument.market,
                bars=[],
                data_status="data_empty",
                degradation_reasons=_with_cache_error(
                    cache_read_error,
                    f"akshare_empty:{instrument.symbol}",
                ),
                source="akshare",
                cache_status=cache_status,
            )

        try:
            bars = _standardize_rows(rows)
        except ValueError as exc:
            return MarketSeries(
                name=instrument.name,
                symbol=instrument.symbol,
                market=instrument.market,
                bars=[],
                data_status="field_mismatch",
                degradation_reasons=_with_cache_error(
                    cache_read_error,
                    f"akshare_field_mismatch:{exc}",
                ),
                source="akshare",
                cache_status=cache_status,
            )

        self._write_cache(cache_path, bars)
        return MarketSeries(
            name=instrument.name,
            symbol=instrument.symbol,
            market=instrument.market,
            bars=bars,
            source="akshare",
            cache_status=cache_status,
        )

    def _cache_path(self, normalized_symbol: str) -> Path:
        return self.cache_dir / "akshare" / f"{normalized_symbol}.json"

    def _read_cache(self, path: Path) -> list[DailyBar] | None:
        if not path.exists():
            return None
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            raise ValueError("cache_root_not_list")
        return [DailyBar(**item) for item in loaded]

    def _write_cache(self, path: Path, bars: list[DailyBar]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([asdict(bar) for bar in bars], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _raw_rows(raw: object) -> list[dict[str, Any]]:
    if hasattr(raw, "to_dict"):
        records = raw.to_dict("records")
    else:
        records = raw
    if records is None:
        return []
    if not isinstance(records, list):
        raise ValueError("raw_rows_not_list")
    return [dict(row) for row in records]


def _standardize_rows(rows: list[dict[str, Any]]) -> list[DailyBar]:
    bars: list[DailyBar] = []
    previous_close: float | None = None
    for row in sorted(rows, key=lambda item: str(_pick(item, ("日期", "trade_date", "date")))):
        close = _float_value(_pick(row, ("收盘", "close")))
        prev_close = previous_close if previous_close is not None else close
        bars.append(
            DailyBar(
                trade_date=_date_text(_pick(row, ("日期", "trade_date", "date"))),
                open=_float_value(_pick(row, ("开盘", "open"))),
                high=_float_value(_pick(row, ("最高", "high"))),
                low=_float_value(_pick(row, ("最低", "low"))),
                close=close,
                volume=_int_value(_pick(row, ("成交量", "volume"))),
                amount=_float_value(_pick(row, ("成交额", "amount"))),
                prev_close=prev_close,
            )
        )
        if close is not None:
            previous_close = close
    return bars


def _normalize_symbol(symbol: str) -> str:
    stripped = symbol.strip()
    if "." in stripped:
        return stripped.split(".", 1)[0]
    if len(stripped) > 6 and stripped[:2].isalpha():
        return stripped[-6:]
    return stripped


def _pick(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    raise ValueError(f"missing_field:{'/'.join(keys)}")


def _date_text(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value).replace("/", "-")[:10]


def _float_value(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(str(value).replace(",", ""))


def _int_value(value: Any) -> int | None:
    parsed = _float_value(value)
    if parsed is None:
        return None
    return int(parsed)


def _cache_read_error_reason(exc: Exception) -> str:
    if isinstance(exc, json.JSONDecodeError):
        return "cache_read_error:invalid_json"
    if isinstance(exc, OSError):
        return "cache_read_error:io_error"
    return "cache_read_error:schema_invalid"


def _with_cache_error(cache_read_error: str | None, reason: str) -> list[str]:
    if cache_read_error is None:
        return [reason]
    return [cache_read_error, reason]
