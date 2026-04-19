from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.schemas.music import CreateMusicRequest, MusicListResponse, NormalizedMusicResult
from app.services.music_service import MusicService


router = APIRouter(prefix="/api/v1/music", tags=["music"])
service = MusicService()


@router.post("", response_model=NormalizedMusicResult, status_code=201)
def create_music(payload: CreateMusicRequest) -> NormalizedMusicResult:
    return service.create_music(payload)


@router.get("", response_model=MusicListResponse)
def list_music(limit: int = Query(default=20, ge=1, le=100)) -> MusicListResponse:
    return MusicListResponse(items=service.list_music(limit=limit))


@router.get("/{request_id}", response_model=NormalizedMusicResult)
def get_music(request_id: str) -> NormalizedMusicResult:
    item = service.get_music(request_id)
    if not item:
        raise HTTPException(status_code=404, detail="Request not found.")
    return item


@router.get("/{request_id}/download")
def download_music(request_id: str) -> RedirectResponse:
    item = service.get_music(request_id)
    if not item:
        raise HTTPException(status_code=404, detail="Request not found.")
    if not item.mp3Url:
        raise HTTPException(status_code=409, detail="Audio is not ready yet.")
    return RedirectResponse(item.mp3Url, status_code=307)
