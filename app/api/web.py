from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import ROOT_DIR, get_settings


router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=str(ROOT_DIR / "app" / "templates"))
settings = get_settings()


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
            "acestep_base_url": settings.acestep_base_url,
        },
    )
