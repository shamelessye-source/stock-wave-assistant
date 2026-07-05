from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_web_mvp_has_unified_api_client() -> None:
    api_client = ROOT / "web" / "src" / "api" / "client.ts"

    assert api_client.exists()
    text = api_client.read_text(encoding="utf-8")
    assert "export async function apiGet" in text
    assert "export async function apiPost" in text
    assert "export async function apiPut" in text
    assert "ApiResult" in text


def test_web_mvp_declares_required_tool_tabs() -> None:
    app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")

    for tab_id in [
        "overview",
        "indicators",
        "risk",
        "wave",
        "ledger",
        "report",
        "settings",
    ]:
        assert f'id: "{tab_id}"' in app


def test_web_mvp_exposes_watchlist_editor() -> None:
    app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")

    assert "WatchlistEditor" in app
    assert '"/api/watchlist"' in app
    assert '"/api/watchlist/validate"' in app
