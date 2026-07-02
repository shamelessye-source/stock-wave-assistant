from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.config import router as config_router
from app.api.routes.indicators import router as indicators_router
from app.api.routes.ledger import router as ledger_router
from app.api.routes.market import router as market_router
from app.api.routes.reports import router as reports_router
from app.api.routes.risk import router as risk_router
from app.api.routes.wave import router as wave_router


app = FastAPI(
    title="Stock Wave Assistant",
    description="Local research and review assistant. Not investment advice.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(config_router)
app.include_router(market_router)
app.include_router(indicators_router)
app.include_router(ledger_router)
app.include_router(risk_router)
app.include_router(wave_router)
app.include_router(reports_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "stock-wave-assistant",
        "mode": "mock",
    }
