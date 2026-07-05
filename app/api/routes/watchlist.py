from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException

from app.core.config import load_settings
from app.schemas.watchlist import (
    WatchlistConfigPayload,
    WatchlistValidationResponse,
)
from app.services.watchlist_service import (
    WatchlistConfigError,
    load_watchlist,
    save_watchlist,
    validate_watchlist_payload,
)


router = APIRouter()


@router.get("/api/watchlist", response_model=WatchlistConfigPayload)
def watchlist_get() -> dict[str, object]:
    settings = load_settings()
    return _service_response(lambda: load_watchlist(settings.config_dir / "watchlist.yaml"))


@router.put("/api/watchlist", response_model=WatchlistConfigPayload)
def watchlist_put(payload: WatchlistConfigPayload) -> dict[str, object]:
    settings = load_settings()
    return _service_response(
        lambda: save_watchlist(
            settings.config_dir / "watchlist.yaml",
            payload.model_dump(),
        )
    )


@router.post("/api/watchlist/validate", response_model=WatchlistValidationResponse)
def watchlist_validate(payload: WatchlistConfigPayload) -> dict[str, object]:
    return validate_watchlist_payload(payload.model_dump())


def _service_response(callback: Callable[[], dict[str, object]]) -> dict[str, object]:
    try:
        return callback()
    except WatchlistConfigError as exc:
        status_code = 422 if "invalid_watchlist" in str(exc) else 409
        raise HTTPException(
            status_code=status_code,
            detail={
                "error": str(exc),
                "errors": exc.errors,
            },
        ) from exc
