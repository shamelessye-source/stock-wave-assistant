from fastapi import APIRouter

from app.core.config import load_settings
from app.providers.llm.selfcheck import check_codex_cli


router = APIRouter()


@router.get("/api/config/status")
def config_status() -> dict[str, object]:
    settings = load_settings()
    status = settings.public_status()
    codex_status = check_codex_cli(settings, run_version=False).as_public_dict()
    codex_status.pop("version", None)
    status["codex"] = codex_status
    return status
