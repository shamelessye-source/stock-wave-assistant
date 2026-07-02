from dataclasses import asdict

from fastapi import APIRouter

from app.core.config import load_settings
from app.data.market_provider import create_market_provider
from app.domain.indicators import build_indicator_snapshot


router = APIRouter()


@router.get("/api/indicators/snapshot")
def indicators_snapshot() -> dict[str, object]:
    settings = load_settings()
    provider = create_market_provider(settings)
    items = [
        asdict(build_indicator_snapshot(instrument, provider.daily_bars_for(instrument)))
        for instrument in provider.load_instruments()
    ]
    return {
        "provider": settings.market_provider,
        "items": items,
    }
