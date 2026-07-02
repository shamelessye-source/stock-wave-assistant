from dataclasses import asdict

from fastapi import APIRouter

from app.data.mock_market_provider import MockMarketProvider
from app.domain.indicators import build_indicator_snapshot


router = APIRouter()


@router.get("/api/indicators/snapshot")
def indicators_snapshot() -> dict[str, object]:
    provider = MockMarketProvider()
    items = [
        asdict(build_indicator_snapshot(instrument, provider.daily_bars_for(instrument)))
        for instrument in provider.load_instruments()
    ]
    return {
        "provider": "mock",
        "items": items,
    }
