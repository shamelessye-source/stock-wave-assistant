from pathlib import Path

import pytest
import yaml

from app.services.watchlist_service import (
    WatchlistConfigError,
    load_watchlist,
    save_watchlist,
    validate_watchlist_payload,
)


def test_load_watchlist_normalizes_existing_yaml_fields(tmp_path: Path) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    watchlist_path.write_text(
        """
version: 1
stocks:
  - symbol: 600522.SH
    name: 中天科技
    market: SH
    enabled: true
    group: 核心观察
    direction: 通信设备
    watch_reason: 趋势观察样例
    risk_points:
      - 数据延迟
      - 波动较大
""".strip(),
        encoding="utf-8",
    )

    payload = load_watchlist(watchlist_path)

    assert payload["version"] == 1
    assert payload["items"] == [
        {
            "name": "中天科技",
            "symbol": "600522.SH",
            "market": "SH",
            "group": "核心观察",
            "theme": "通信设备",
            "enabled": True,
            "observation_note": "趋势观察样例",
            "risk_note": "数据延迟\n波动较大",
        }
    ]


def test_save_watchlist_writes_compatible_yaml_atomically(tmp_path: Path) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    payload = {
        "version": 1,
        "items": [
            {
                "name": "示例标的",
                "symbol": "000001.SZ",
                "market": "SZ",
                "group": "观察池",
                "theme": "银行",
                "enabled": False,
                "observation_note": "用于本地验证",
                "risk_note": "数据可能延迟",
            }
        ],
    }

    saved = save_watchlist(watchlist_path, payload)
    raw = yaml.safe_load(watchlist_path.read_text(encoding="utf-8"))

    assert saved["items"][0]["symbol"] == "000001.SZ"
    assert raw["stocks"][0]["direction"] == "银行"
    assert raw["stocks"][0]["watch_reason"] == "用于本地验证"
    assert raw["stocks"][0]["risk_points"] == ["数据可能延迟"]
    assert not list(tmp_path.glob("*.tmp"))


def test_validate_watchlist_payload_reports_format_errors() -> None:
    result = validate_watchlist_payload(
        {
            "version": 1,
            "items": [
                {
                    "name": "",
                    "symbol": "bad-code",
                    "market": "SH",
                    "group": "",
                    "theme": "",
                    "enabled": True,
                    "observation_note": "",
                    "risk_note": "",
                }
            ],
        }
    )

    assert result["valid"] is False
    assert "items[0].name_required" in result["errors"]
    assert "items[0].symbol_format" in result["errors"]


def test_save_watchlist_rejects_invalid_payload_without_touching_file(
    tmp_path: Path,
) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    original = "version: 1\nstocks:\n  - name: 原始标的\n    symbol: ''\n"
    watchlist_path.write_text(original, encoding="utf-8")

    with pytest.raises(WatchlistConfigError):
        save_watchlist(
            watchlist_path,
            {
                "version": 1,
                "items": [
                    {
                        "name": "",
                        "symbol": "bad-code",
                        "market": "",
                        "group": "",
                        "theme": "",
                        "enabled": True,
                        "observation_note": "",
                        "risk_note": "",
                    }
                ],
            },
        )

    assert watchlist_path.read_text(encoding="utf-8") == original


def test_save_watchlist_rejects_empty_items_without_touching_file(
    tmp_path: Path,
) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    original = "version: 1\nstocks:\n  - name: Original\n    symbol: ''\n"
    watchlist_path.write_text(original, encoding="utf-8")

    with pytest.raises(WatchlistConfigError) as exc_info:
        save_watchlist(watchlist_path, {"version": 1, "items": []})

    assert "items_empty" in exc_info.value.errors
    assert watchlist_path.read_text(encoding="utf-8") == original


def test_save_watchlist_rejects_duplicate_names_without_touching_file(
    tmp_path: Path,
) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    original = "version: 1\nstocks:\n  - name: Original\n    symbol: ''\n"
    watchlist_path.write_text(original, encoding="utf-8")

    with pytest.raises(WatchlistConfigError) as exc_info:
        save_watchlist(
            watchlist_path,
            {
                "version": 1,
                "items": [
                    _watchlist_item(name="Alpha", symbol=""),
                    _watchlist_item(name=" Alpha ", symbol=""),
                ],
            },
        )

    assert "name_duplicate:Alpha" in exc_info.value.errors
    assert watchlist_path.read_text(encoding="utf-8") == original


def test_save_watchlist_rejects_duplicate_non_empty_symbols_without_touching_file(
    tmp_path: Path,
) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    original = "version: 1\nstocks:\n  - name: Original\n    symbol: ''\n"
    watchlist_path.write_text(original, encoding="utf-8")

    with pytest.raises(WatchlistConfigError) as exc_info:
        save_watchlist(
            watchlist_path,
            {
                "version": 1,
                "items": [
                    _watchlist_item(name="Alpha", symbol="600522.SH"),
                    _watchlist_item(name="Beta", symbol=" 600522.SH "),
                ],
            },
        )

    assert "symbol_duplicate:600522.SH" in exc_info.value.errors
    assert watchlist_path.read_text(encoding="utf-8") == original


def test_save_watchlist_allows_multiple_empty_symbols(tmp_path: Path) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"

    saved = save_watchlist(
        watchlist_path,
        {
            "version": 1,
            "items": [
                _watchlist_item(name="Alpha", symbol=""),
                _watchlist_item(name="Beta", symbol=""),
            ],
        },
    )

    assert [item["symbol"] for item in saved["items"]] == ["", ""]


def test_load_watchlist_rejects_bad_yaml(tmp_path: Path) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    watchlist_path.write_text("version: 1\nstocks: [", encoding="utf-8")

    with pytest.raises(WatchlistConfigError, match="invalid_yaml"):
        load_watchlist(watchlist_path)


@pytest.mark.parametrize("bad_entry", ["plain-text", ["nested-list"]])
def test_load_watchlist_rejects_non_object_stock_entries(
    tmp_path: Path,
    bad_entry: object,
) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    original = yaml.safe_dump(
        {
            "version": 1,
            "stocks": [
                {"name": "Alpha", "symbol": ""},
                bad_entry,
            ],
        },
        allow_unicode=True,
        sort_keys=False,
    )
    watchlist_path.write_text(original, encoding="utf-8")

    with pytest.raises(WatchlistConfigError) as exc_info:
        load_watchlist(watchlist_path)

    assert "stocks[1].not_object" in exc_info.value.errors
    assert watchlist_path.read_text(encoding="utf-8") == original


def _watchlist_item(name: str, symbol: str) -> dict[str, object]:
    return {
        "name": name,
        "symbol": symbol,
        "market": "",
        "group": "",
        "theme": "",
        "enabled": True,
        "observation_note": "",
        "risk_note": "",
    }
