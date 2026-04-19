from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas.music import CreateMusicRequest, MusicItem, PrototypeUserItem


settings = get_settings()
SCHEMA = settings.db_schema


def _json_dump(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def _music_status_cast(bind_name: str) -> str:
    return f'CAST(:{bind_name} AS "{SCHEMA}"."MusicStatus")'


def _job_type_cast(bind_name: str) -> str:
    return f'CAST(:{bind_name} AS "{SCHEMA}"."JobType")'


def _job_target_type_cast(bind_name: str) -> str:
    return f'CAST(:{bind_name} AS "{SCHEMA}"."JobTargetType")'


def _queue_status_cast(bind_name: str) -> str:
    return f'CAST(:{bind_name} AS "{SCHEMA}"."QueueStatus")'


def _row_to_item(row: Any) -> MusicItem:
    mapping = row._mapping
    return MusicItem(
        id=mapping["id"],
        title=(mapping["title"] or "ACE-Step Track").strip(),
        status=str(mapping["status"]).lower(),
        provider=mapping["provider"],
        providerTaskId=mapping["providerTaskId"],
        lyrics=mapping["lyrics"],
        stylePrompt=mapping["stylePrompt"],
        imageUrl=mapping["imageUrl"],
        mp3Url=mapping["mp3Url"],
        duration=mapping["duration"],
        errorMessage=mapping["errorMessage"],
        isPublic=mapping["isPublic"],
        createdAt=mapping["createdAt"],
        updatedAt=mapping["updatedAt"],
        rawStatus=mapping["rawStatus"],
    )


def user_exists(session: Session, user_id: str) -> bool:
    row = session.execute(
        text(
            f'''
            SELECT 1
            FROM "{SCHEMA}"."User"
            WHERE "id" = :id
            LIMIT 1
            '''
        ),
        {"id": user_id},
    ).one_or_none()
    return row is not None


def list_recent_users(session: Session, limit: int = 20) -> list[PrototypeUserItem]:
    rows = session.execute(
        text(
            f'''
            SELECT "id", "email", "name"
            FROM "{SCHEMA}"."User"
            ORDER BY "createdAt" DESC
            LIMIT :limit
            '''
        ),
        {"limit": limit},
    ).all()

    return [
        PrototypeUserItem(
            id=row.id,
            email=row.email,
            name=row.name,
        )
        for row in rows
    ]


def create_music(
    session: Session,
    payload: CreateMusicRequest,
    *,
    title: str,
    raw_payload: dict[str, Any],
) -> MusicItem:
    now = datetime.utcnow()
    music_id = f"ace_{uuid4().hex}"

    query = text(
        f'''
        INSERT INTO "{SCHEMA}"."Music" (
          "id", "userId", "requestGroupId", "isPublic", "title", "lyrics", "stylePrompt",
          "isMr", "provider", "providerTaskId", "mp3Url", "imageUrl", "videoUrl",
          "rawStatus", "rawPayload", "rawResponse", "isBonusTrack", "status",
          "duration", "tags", "errorMessage", "createdAt", "updatedAt"
        )
        VALUES (
          :id, :user_id, :request_group_id, :is_public, :title, :lyrics, :style_prompt,
          false, :provider, NULL, NULL, NULL, NULL,
          :raw_status, CAST(:raw_payload AS JSONB), NULL, false, {_music_status_cast("status")},
          NULL, NULL, NULL, :created_at, :updated_at
        )
        RETURNING
          "id", "title", "status", "provider", "providerTaskId", "lyrics", "stylePrompt",
          "imageUrl", "mp3Url", "duration", "errorMessage", "isPublic", "createdAt",
          "updatedAt", "rawStatus"
        '''
    )

    row = session.execute(
        query,
        {
            "id": music_id,
            "user_id": payload.userId,
            "request_group_id": f"group_{uuid4().hex}",
            "is_public": payload.isPublic,
            "title": title,
            "lyrics": payload.lyrics,
            "style_prompt": payload.stylePrompt,
            "provider": "ACE_STEP",
            "raw_status": "queued",
            "raw_payload": _json_dump(raw_payload),
            "status": "QUEUED",
            "created_at": now,
            "updated_at": now,
        },
    ).one()

    return _row_to_item(row)


def create_generation_job(session: Session, *, user_id: str, music_id: str, payload: dict[str, Any]) -> str:
    job_id = f"job_{uuid4().hex}"
    now = datetime.utcnow()
    query = text(
        f'''
        INSERT INTO "{SCHEMA}"."GenerationJob" (
          "id", "userId", "musicId", "targetType", "jobType", "queueStatus",
          "priority", "attemptCount", "maxAttempts", "runAfter", "payload",
          "createdAt", "updatedAt"
        )
        VALUES (
          :id, :user_id, :music_id, {_job_target_type_cast("target_type")},
          {_job_type_cast("job_type")}, {_queue_status_cast("queue_status")},
          100, 0, 6, :run_after, CAST(:payload AS JSONB), :created_at, :updated_at
        )
        '''
    )

    session.execute(
        query,
        {
            "id": job_id,
            "user_id": user_id,
            "music_id": music_id,
            "target_type": "MUSIC",
            "job_type": "MUSIC_GENERATION",
            "queue_status": "QUEUED",
            "run_after": now,
            "payload": _json_dump(payload),
            "created_at": now,
            "updated_at": now,
        },
    )
    return job_id


def mark_job_active(session: Session, job_id: str) -> None:
    session.execute(
        text(
            f'''
            UPDATE "{SCHEMA}"."GenerationJob"
            SET "queueStatus" = {_queue_status_cast("queue_status")},
                "startedAt" = :started_at,
                "lockedAt" = :locked_at,
                "lockedBy" = :locked_by,
                "updatedAt" = :updated_at
            WHERE "id" = :id
            '''
        ),
        {
            "id": job_id,
            "queue_status": "ACTIVE",
            "started_at": datetime.utcnow(),
            "locked_at": datetime.utcnow(),
            "locked_by": "ace-step-prototype",
            "updated_at": datetime.utcnow(),
        },
    )


def finish_job(session: Session, job_id: str, *, status: str, result: Any = None, error_message: str | None = None) -> None:
    session.execute(
        text(
            f'''
            UPDATE "{SCHEMA}"."GenerationJob"
            SET "queueStatus" = {_queue_status_cast("queue_status")},
                "finishedAt" = :finished_at,
                "lockedAt" = NULL,
                "lockedBy" = NULL,
                "errorMessage" = :error_message,
                "result" = CAST(:result AS JSONB),
                "updatedAt" = :updated_at
            WHERE "id" = :id
            '''
        ),
        {
            "id": job_id,
            "queue_status": status,
            "finished_at": datetime.utcnow(),
            "error_message": error_message,
            "result": _json_dump(result),
            "updated_at": datetime.utcnow(),
        },
    )


def update_music_provider_ack(
    session: Session,
    *,
    music_id: str,
    provider_task_id: str,
    raw_response: Any,
) -> None:
    session.execute(
        text(
            f'''
            UPDATE "{SCHEMA}"."Music"
            SET "providerTaskId" = :provider_task_id,
                "rawStatus" = :raw_status,
                "rawResponse" = CAST(:raw_response AS JSONB),
                "updatedAt" = :updated_at
            WHERE "id" = :id
            '''
        ),
        {
            "id": music_id,
            "provider_task_id": provider_task_id,
            "raw_status": "queued",
            "raw_response": _json_dump(raw_response),
            "updated_at": datetime.utcnow(),
        },
    )


def mark_music_processing(session: Session, *, music_id: str, raw_response: Any | None = None) -> None:
    session.execute(
        text(
            f'''
            UPDATE "{SCHEMA}"."Music"
            SET "status" = {_music_status_cast("status")},
                "rawStatus" = :raw_status,
                "rawResponse" = COALESCE(CAST(:raw_response AS JSONB), "rawResponse"),
                "updatedAt" = :updated_at
            WHERE "id" = :id
            '''
        ),
        {
            "id": music_id,
            "status": "PROCESSING",
            "raw_status": "processing",
            "raw_response": _json_dump(raw_response),
            "updated_at": datetime.utcnow(),
        },
    )


def complete_music(
    session: Session,
    *,
    music_id: str,
    title: str,
    mp3_url: str,
    image_url: str,
    duration: int | None,
    provider_task_id: str,
    raw_response: Any,
) -> None:
    session.execute(
        text(
            f'''
            UPDATE "{SCHEMA}"."Music"
            SET "title" = :title,
                "providerTaskId" = :provider_task_id,
                "mp3Url" = :mp3_url,
                "imageUrl" = :image_url,
                "duration" = :duration,
                "status" = {_music_status_cast("status")},
                "rawStatus" = :raw_status,
                "rawResponse" = CAST(:raw_response AS JSONB),
                "errorMessage" = NULL,
                "updatedAt" = :updated_at
            WHERE "id" = :id
            '''
        ),
        {
            "id": music_id,
            "title": title,
            "provider_task_id": provider_task_id,
            "mp3_url": mp3_url,
            "image_url": image_url,
            "duration": duration,
            "status": "COMPLETED",
            "raw_status": "completed",
            "raw_response": _json_dump(raw_response),
            "updated_at": datetime.utcnow(),
        },
    )


def fail_music(session: Session, *, music_id: str, error_message: str, raw_response: Any | None = None) -> None:
    session.execute(
        text(
            f'''
            UPDATE "{SCHEMA}"."Music"
            SET "status" = {_music_status_cast("status")},
                "rawStatus" = :raw_status,
                "rawResponse" = COALESCE(CAST(:raw_response AS JSONB), "rawResponse"),
                "errorMessage" = :error_message,
                "updatedAt" = :updated_at
            WHERE "id" = :id
            '''
        ),
        {
            "id": music_id,
            "status": "FAILED",
            "raw_status": "failed",
            "raw_response": _json_dump(raw_response),
            "error_message": error_message,
            "updated_at": datetime.utcnow(),
        },
    )


def get_music(session: Session, music_id: str) -> MusicItem | None:
    row = session.execute(
        text(
            f'''
            SELECT
              "id", "title", "status", "provider", "providerTaskId", "lyrics", "stylePrompt",
              "imageUrl", "mp3Url", "duration", "errorMessage", "isPublic", "createdAt",
              "updatedAt", "rawStatus"
            FROM "{SCHEMA}"."Music"
            WHERE "id" = :id
            '''
        ),
        {"id": music_id},
    ).one_or_none()

    return _row_to_item(row) if row else None


def list_music(session: Session, limit: int = 20) -> list[MusicItem]:
    rows = session.execute(
        text(
            f'''
            SELECT
              "id", "title", "status", "provider", "providerTaskId", "lyrics", "stylePrompt",
              "imageUrl", "mp3Url", "duration", "errorMessage", "isPublic", "createdAt",
              "updatedAt", "rawStatus"
            FROM "{SCHEMA}"."Music"
            WHERE "provider" = 'ACE_STEP'
            ORDER BY "createdAt" DESC
            LIMIT :limit
            '''
        ),
        {"limit": limit},
    ).all()

    return [_row_to_item(row) for row in rows]
