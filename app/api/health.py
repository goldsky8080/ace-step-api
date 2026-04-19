from __future__ import annotations

from fastapi import APIRouter

from app.schemas.music import HealthResponse
from app.services.ace_client import AceStepClient


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    acestep_ok = False

    try:
        acestep_ok = AceStepClient().health_check()
    except Exception:
        acestep_ok = False

    return HealthResponse(ok=acestep_ok, acestep=acestep_ok)
