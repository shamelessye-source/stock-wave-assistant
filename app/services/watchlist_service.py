from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any, Mapping

import yaml


SYMBOL_PATTERN = re.compile(r"^\d{6}\.(SH|SZ|BJ)$")
MARKETS = {"", "SH", "SZ", "BJ"}


class WatchlistConfigError(RuntimeError):
    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or [message]


def load_watchlist(path: str | Path) -> dict[str, Any]:
    config = _read_watchlist_yaml(Path(path))
    stocks = config.get("stocks")
    if not isinstance(stocks, list):
        raise WatchlistConfigError("stocks_required")
    errors = [
        f"stocks[{index}].not_object"
        for index, item in enumerate(stocks)
        if not isinstance(item, Mapping)
    ]
    if errors:
        raise WatchlistConfigError("invalid_watchlist", errors)
    return {
        "version": int(config.get("version") or 1),
        "items": [_normalize_item(item) for item in stocks],
    }


def validate_watchlist_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    errors = _validation_errors(payload)
    return {
        "valid": not errors,
        "errors": errors,
    }


def save_watchlist(path: str | Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    errors = _validation_errors(payload)
    if errors:
        raise WatchlistConfigError("invalid_watchlist", errors)

    target_path = Path(path)
    normalized = _normalize_payload(payload)
    raw_config = {
        "version": normalized["version"],
        "stocks": [_to_yaml_stock(item) for item in normalized["items"]],
    }
    _write_yaml_atomic(target_path, raw_config)
    return load_watchlist(target_path)


def _read_watchlist_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise WatchlistConfigError("watchlist_not_found")
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise WatchlistConfigError("invalid_yaml") from exc
    if not isinstance(loaded, dict):
        raise WatchlistConfigError("invalid_yaml_root")
    return loaded


def _validation_errors(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    items = payload.get("items")
    if not isinstance(items, list):
        return ["items_required"]
    if not items:
        return ["items_empty"]

    seen_names: set[str] = set()
    seen_symbols: set[str] = set()
    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, Mapping):
            errors.append(f"items[{index}].invalid")
            continue
        name = _text(raw_item.get("name"))
        symbol = _text(raw_item.get("symbol")).upper()
        market = _text(raw_item.get("market")).upper()
        if not name:
            errors.append(f"items[{index}].name_required")
        elif name in seen_names:
            errors.append(f"name_duplicate:{name}")
        else:
            seen_names.add(name)
        if symbol and not SYMBOL_PATTERN.match(symbol):
            errors.append(f"items[{index}].symbol_format")
        elif symbol and symbol in seen_symbols:
            errors.append(f"symbol_duplicate:{symbol}")
        elif symbol:
            seen_symbols.add(symbol)
        if market not in MARKETS:
            errors.append(f"items[{index}].market_format")
    return errors


def _normalize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "version": int(payload.get("version") or 1),
        "items": [_normalize_item(item) for item in payload.get("items", [])],
    }


def _normalize_item(item: Mapping[str, Any]) -> dict[str, Any]:
    theme = _text(item.get("theme")) or _text(item.get("direction"))
    return {
        "name": _text(item.get("name")),
        "symbol": _text(item.get("symbol")).upper(),
        "market": _text(item.get("market")).upper(),
        "group": _text(item.get("group")),
        "theme": theme,
        "enabled": _bool(item.get("enabled", True)),
        "observation_note": _text(item.get("observation_note"))
        or _text(item.get("watch_reason")),
        "risk_note": _risk_note(item),
    }


def _to_yaml_stock(item: Mapping[str, Any]) -> dict[str, Any]:
    risk_note = _text(item.get("risk_note"))
    return {
        "symbol": _text(item.get("symbol")),
        "name": _text(item.get("name")),
        "market": _text(item.get("market")),
        "enabled": _bool(item.get("enabled", True)),
        "group": _text(item.get("group")),
        "theme": _text(item.get("theme")),
        "direction": _text(item.get("theme")),
        "observation_note": _text(item.get("observation_note")),
        "watch_reason": _text(item.get("observation_note")),
        "risk_note": risk_note,
        "risk_points": [line.strip() for line in risk_note.splitlines() if line.strip()],
    }


def _write_yaml_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=path.parent,
            encoding="utf-8",
            prefix=f".{path.stem}.",
            suffix=".tmp",
        ) as handle:
            temp_path = Path(handle.name)
            yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)
        temp_path.replace(path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _risk_note(item: Mapping[str, Any]) -> str:
    risk_note = _text(item.get("risk_note"))
    if risk_note:
        return risk_note
    risk_points = item.get("risk_points")
    if isinstance(risk_points, list):
        return "\n".join(_text(point) for point in risk_points if _text(point))
    return ""


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return bool(value)
