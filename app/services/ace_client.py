from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import get_settings
from app.schemas.music import AceTaskSummary, CreateMusicRequest, QueryTaskResult


settings = get_settings()


class AceStepClient:
    def __init__(self) -> None:
        self.base_url = settings.acestep_base_url
        self.api_key = settings.acestep_api_key

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def health_check(self) -> bool:
        response = httpx.get(f"{self.base_url}/health", timeout=10.0)
        response.raise_for_status()
        return True

    def create_task(self, payload: CreateMusicRequest) -> AceTaskSummary:
        model_name = payload.model or "acestep-v15-turbo"
        duration_seconds = payload.duration or 90
        request_body = {
            "prompt": payload.prompt or payload.stylePrompt,
            "lyrics": payload.lyrics,
            "vocal_language": payload.vocalLanguage,
            "audio_format": "mp3",
            "thinking": payload.thinking,
            "model": model_name,
            "audio_duration": duration_seconds,
        }

        try:
            response = httpx.post(
                f"{self.base_url}/release_task",
                json=request_body,
                headers=self._headers(),
                timeout=settings.acestep_request_timeout_seconds,
            )
        except httpx.TimeoutException as error:
            raise RuntimeError(
                "ACE-Step release_task timed out. The API server is reachable, but model loading or task acceptance is taking too long."
            ) from error
        response.raise_for_status()
        body = response.json()
        data = body.get("data") or {}

        return AceTaskSummary(
            taskId=data["task_id"],
            status="queued",
            queuePosition=data.get("queue_position"),
        )

    def query_task(self, task_id: str) -> QueryTaskResult:
        try:
            response = httpx.post(
                f"{self.base_url}/query_result",
                json={"task_id_list": [task_id]},
                headers=self._headers(),
                timeout=settings.acestep_poll_timeout_seconds,
            )
        except httpx.TimeoutException as error:
            raise RuntimeError("ACE-Step query_result timed out while waiting for task status.") from error
        response.raise_for_status()
        body = response.json()
        items = body.get("data") or []
        if not items:
            raise RuntimeError("ACE-Step returned an empty task result.")

        item = items[0]
        status_code = int(item.get("status", 0))
        parsed_result = self._parse_result(item.get("result"))
        first = parsed_result[0] if parsed_result else {}
        audio_url = self._normalize_audio_url(first.get("file"))
        metas = first.get("metas") if isinstance(first.get("metas"), dict) else {}

        return QueryTaskResult(
          taskId=item.get("task_id", task_id),
          statusCode=status_code,
          status=self._map_status(status_code),
          audioUrl=audio_url,
          prompt=first.get("prompt"),
          lyrics=first.get("lyrics"),
          duration=self._parse_duration(metas.get("duration")),
          model=first.get("dit_model"),
          raw=item,
        )

    def _parse_result(self, result: Any) -> list[dict[str, Any]]:
        if result is None:
            return []
        if isinstance(result, list):
            return [entry for entry in result if isinstance(entry, dict)]
        if isinstance(result, str):
            try:
                parsed = json.loads(result)
            except json.JSONDecodeError:
                return []
            if isinstance(parsed, list):
                return [entry for entry in parsed if isinstance(entry, dict)]
        return []

    def _normalize_audio_url(self, file_value: Any) -> str | None:
        if not isinstance(file_value, str) or not file_value:
            return None
        if file_value.startswith("http://") or file_value.startswith("https://"):
            return file_value
        if file_value.startswith("/"):
            return f"{self.base_url}{file_value}"
        return f"{self.base_url}/v1/audio?path={file_value}"

    def _parse_duration(self, value: Any) -> int | None:
        if isinstance(value, (int, float)):
            return int(round(value))
        if isinstance(value, str):
            try:
                return int(round(float(value)))
            except ValueError:
                return None
        return None

    def _map_status(self, status_code: int) -> str:
        if status_code == 1:
            return "completed"
        if status_code == 2:
            return "failed"
        return "processing"
