from __future__ import annotations

from fastapi import APIRouter

from app.core.config import load_settings
from app.schemas.wave_state import WaveStatesResponse
from app.services.portfolio_service import (
    build_current_wave_states,
    decimal_dataclass_to_response,
)


router = APIRouter()


@router.get("/api/wave/states", response_model=WaveStatesResponse)
def wave_states() -> dict[str, object]:
    settings = load_settings()
    return {
        "items": [
            decimal_dataclass_to_response(item)
            for item in build_current_wave_states(settings)
        ],
    }
