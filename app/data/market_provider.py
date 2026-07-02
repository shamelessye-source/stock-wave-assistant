from __future__ import annotations

from app.core.config import AppSettings
from app.data.akshare_market_provider import AkShareMarketProvider
from app.data.mock_market_provider import MockMarketProvider


def create_market_provider(settings: AppSettings) -> MockMarketProvider | AkShareMarketProvider:
    if settings.market_provider == "akshare":
        return AkShareMarketProvider(
            watchlist_path=settings.config_dir / "watchlist.yaml",
            cache_dir=settings.cache_dir,
        )
    return MockMarketProvider(settings.config_dir / "watchlist.yaml")
