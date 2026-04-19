from __future__ import annotations

from threading import Lock

from app.schemas.music import NormalizedMusicResult


class JobStore:
    def __init__(self) -> None:
        self._items: dict[str, NormalizedMusicResult] = {}
        self._lock = Lock()

    def upsert(self, item: NormalizedMusicResult) -> None:
        with self._lock:
            self._items[item.requestId] = item

    def get(self, request_id: str) -> NormalizedMusicResult | None:
        with self._lock:
            return self._items.get(request_id)

    def list(self, limit: int = 20) -> list[NormalizedMusicResult]:
        with self._lock:
            items = sorted(
                self._items.values(),
                key=lambda item: item.createdAt,
                reverse=True,
            )
            return items[:limit]
