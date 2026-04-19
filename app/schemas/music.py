from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


MusicStatus = Literal["queued", "processing", "completed", "failed"]


class CreateMusicRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    lyrics: str = Field(default="", max_length=5000)
    stylePrompt: str = Field(..., min_length=2, max_length=900)
    prompt: str | None = Field(default=None, max_length=900)
    vocalLanguage: str = Field(default="ko", max_length=12)
    model: str | None = Field(default=None, max_length=120)
    modelVersion: str | None = Field(default=None, max_length=120)
    duration: float | None = Field(default=None, ge=10, le=600)
    thinking: bool = False


class NormalizedMusicResult(BaseModel):
    requestId: str
    provider: str
    providerTaskId: str | None = None
    status: MusicStatus
    title: str
    lyrics: str
    stylePrompt: str
    imageUrl: str | None = None
    mp3Url: str | None = None
    duration: int | None = None
    errorMessage: str | None = None
    raw: dict[str, Any] | list[Any] | str | None = None
    createdAt: datetime
    updatedAt: datetime


class MusicListResponse(BaseModel):
    items: list[NormalizedMusicResult]


class HealthResponse(BaseModel):
    ok: bool
    acestep: bool


class AceTaskSummary(BaseModel):
    taskId: str
    status: MusicStatus
    queuePosition: int | None = None


class QueryTaskResult(BaseModel):
    taskId: str
    statusCode: int
    status: MusicStatus
    audioUrl: str | None = None
    prompt: str | None = None
    lyrics: str | None = None
    duration: int | None = None
    model: str | None = None
    raw: dict[str, Any] | list[Any] | str | None = None
