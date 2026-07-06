from __future__ import annotations

from pydantic import BaseModel


class WatchlistItemPayload(BaseModel):
    name: str = ""
    symbol: str = ""
    market: str = ""
    group: str = ""
    theme: str = ""
    enabled: bool = True
    observation_note: str = ""
    risk_note: str = ""


class WatchlistConfigPayload(BaseModel):
    version: int = 1
    items: list[WatchlistItemPayload]


class WatchlistValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
