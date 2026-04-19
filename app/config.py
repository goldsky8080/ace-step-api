from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _parse_schema(database_url: str) -> str:
    parsed = urlparse(database_url)
    params = parse_qs(parsed.query)
    return params.get("schema", ["public"])[0]


def _normalize_database_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    params = parse_qs(parsed.query)
    params.pop("schema", None)
    sanitized_query = urlencode(params, doseq=True)

    normalized = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            sanitized_query,
            parsed.fragment,
        )
    )

    database_url = normalized
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    app_host: str
    app_port: int
    public_base_url: str
    database_url: str
    db_schema: str
    acestep_base_url: str
    acestep_api_key: str | None
    acestep_request_timeout_seconds: int
    acestep_poll_timeout_seconds: int
    poll_interval_seconds: int
    max_poll_attempts: int
    storage_dir: Path
    audio_dir: Path
    image_dir: Path
    metadata_dir: Path


def get_settings() -> Settings:
    raw_database_url = os.getenv(
        "DATABASE_URL",
        'postgresql://postgres:1469@localhost:5432/music_platform?schema=songsai_api',
    )
    database_url = _normalize_database_url(raw_database_url)
    storage_dir = ROOT_DIR / "storage"

    return Settings(
        app_name=os.getenv("APP_NAME", "ACE-Step API Prototype"),
        app_env=os.getenv("APP_ENV", "development"),
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=int(os.getenv("APP_PORT", "8200")),
        public_base_url=os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8200").rstrip("/"),
        database_url=database_url,
        db_schema=os.getenv("DB_SCHEMA", _parse_schema(raw_database_url)),
        acestep_base_url=os.getenv("ACESTEP_BASE_URL", "http://127.0.0.1:8001").rstrip("/"),
        acestep_api_key=os.getenv("ACESTEP_API_KEY") or None,
        acestep_request_timeout_seconds=int(os.getenv("ACESTEP_REQUEST_TIMEOUT_SECONDS", "600")),
        acestep_poll_timeout_seconds=int(os.getenv("ACESTEP_POLL_TIMEOUT_SECONDS", "120")),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "10")),
        max_poll_attempts=int(os.getenv("MAX_POLL_ATTEMPTS", "90")),
        storage_dir=storage_dir,
        audio_dir=storage_dir / "audio",
        image_dir=storage_dir / "images",
        metadata_dir=storage_dir / "metadata",
    )
