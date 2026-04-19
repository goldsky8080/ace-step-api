from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import uuid4

from app.config import get_settings
from app.schemas.music import CreateMusicRequest, NormalizedMusicResult
from app.services.ace_client import AceStepClient
from app.services.job_store import JobStore
from app.services.storage_service import create_cover_svg, download_audio_to_storage
from app.services.title_service import build_music_title


settings = get_settings()


class MusicService:
    def __init__(self, store: JobStore | None = None) -> None:
        self.ace_client = AceStepClient()
        self.store = store or JobStore()

    def create_music(self, payload: CreateMusicRequest) -> NormalizedMusicResult:
        request_id = f"ace_req_{uuid4().hex}"
        created_at = datetime.now(timezone.utc)
        initial_title = build_music_title(payload)

        queued = NormalizedMusicResult(
            requestId=request_id,
            provider="ACE_STEP",
            providerTaskId=None,
            status="queued",
            title=initial_title,
            lyrics=payload.lyrics,
            stylePrompt=payload.stylePrompt,
            imageUrl=None,
            mp3Url=None,
            duration=None,
            errorMessage=None,
            raw={
                "requestPayload": payload.model_dump(),
            },
            createdAt=created_at,
            updatedAt=created_at,
        )
        self.store.upsert(queued)
        current = queued

        try:
            task = self.ace_client.create_task(payload)

            processing = queued.model_copy(
                update={
                    "providerTaskId": task.taskId,
                    "status": "processing",
                    "raw": {
                        **(queued.raw or {}),
                        "taskAccepted": task.model_dump(),
                    },
                    "updatedAt": datetime.now(timezone.utc),
                }
            )
            self.store.upsert(processing)
            current = processing

            for _ in range(settings.max_poll_attempts):
                result = self.ace_client.query_task(task.taskId)

                if result.status == "completed" and result.audioUrl:
                    final_title = build_music_title(
                        payload.model_copy(update={"title": payload.title or result.prompt or payload.stylePrompt})
                    )
                    stored_audio_url = download_audio_to_storage(result.audioUrl, request_id)
                    stored_image_url = create_cover_svg(final_title, request_id)

                    completed = processing.model_copy(
                        update={
                            "providerTaskId": task.taskId,
                            "status": "completed",
                            "title": final_title,
                            "lyrics": result.lyrics or payload.lyrics,
                            "stylePrompt": payload.stylePrompt,
                            "imageUrl": stored_image_url,
                            "mp3Url": stored_audio_url,
                            "duration": result.duration,
                            "errorMessage": None,
                            "raw": {
                                **(processing.raw or {}),
                                "engineResult": result.model_dump(),
                            },
                            "updatedAt": datetime.now(timezone.utc),
                        }
                    )
                    self.store.upsert(completed)
                    return completed

                if result.status == "failed":
                    failed = current.model_copy(
                        update={
                            "status": "failed",
                            "errorMessage": "ACE-Step task failed.",
                            "raw": {
                                **(current.raw or {}),
                                "engineResult": result.model_dump(),
                            },
                            "updatedAt": datetime.now(timezone.utc),
                        }
                    )
                    self.store.upsert(failed)
                    return failed

                time.sleep(settings.poll_interval_seconds)

            raise TimeoutError("ACE-Step task polling timed out before a completed asset was available.")
        except Exception as error:
            failed = current.model_copy(
                update={
                    "status": "failed",
                    "errorMessage": str(error),
                    "updatedAt": datetime.now(timezone.utc),
                }
            )
            self.store.upsert(failed)
            return failed

    def list_music(self, limit: int = 20) -> list[NormalizedMusicResult]:
        return self.store.list(limit=limit)

    def get_music(self, request_id: str) -> NormalizedMusicResult | None:
        return self.store.get(request_id)
