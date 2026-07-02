from dataclasses import asdict

from fastapi import APIRouter

from app.core.config import load_settings
from app.data.market_provider import create_market_provider


router = APIRouter()


@router.get("/api/market/snapshot")
def market_snapshot() -> dict[str, object]:
    snapshot = create_market_provider(load_settings()).snapshot()
    return asdict(snapshot)
