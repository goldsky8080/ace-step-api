from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.music import router as music_router
from app.api.web import router as web_router
from app.config import ROOT_DIR, get_settings
from app.services.storage_service import ensure_storage_dirs


settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

ensure_storage_dirs()

app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "app" / "static")), name="static")
app.mount("/media/audio", StaticFiles(directory=str(settings.audio_dir)), name="media-audio")
app.mount("/media/images", StaticFiles(directory=str(settings.image_dir)), name="media-images")

app.include_router(web_router)
app.include_router(health_router)
app.include_router(music_router)

