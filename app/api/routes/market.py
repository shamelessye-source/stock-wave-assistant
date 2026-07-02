from dataclasses import asdict

from fastapi import APIRouter

from app.data.mock_market_provider import MockMarketProvider


router = APIRouter()


@router.get("/api/market/snapshot")
def market_snapshot() -> dict[str, object]:
    snapshot = MockMarketProvider().snapshot()
    return asdict(snapshot)
