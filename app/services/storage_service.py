from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.config import get_settings


settings = get_settings()


def ensure_storage_dirs() -> None:
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    settings.image_dir.mkdir(parents=True, exist_ok=True)
    settings.metadata_dir.mkdir(parents=True, exist_ok=True)


def _infer_suffix(url: str, fallback: str) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    return suffix or fallback


def build_public_media_url(kind: str, filename: str) -> str:
    return f"{settings.public_base_url}/media/{kind}/{filename}"


def download_audio_to_storage(source_url: str, music_id: str) -> str:
    suffix = _infer_suffix(source_url, ".mp3")
    file_name = f"{music_id}{suffix}"
    target_path = settings.audio_dir / file_name

    with httpx.stream("GET", source_url, timeout=300.0, follow_redirects=True) as response:
        response.raise_for_status()
        with target_path.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)

    return build_public_media_url("audio", file_name)


def create_cover_svg(title: str, music_id: str) -> str:
    file_name = f"{music_id}.svg"
    target_path = settings.image_dir / file_name
    safe_title = (title or "ACE-Step").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="0 0 1200 1200">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="50%" stop-color="#1d4ed8" />
      <stop offset="100%" stop-color="#14b8a6" />
    </linearGradient>
  </defs>
  <rect width="1200" height="1200" fill="url(#bg)" rx="48" />
  <circle cx="960" cy="220" r="120" fill="rgba(255,255,255,0.12)" />
  <circle cx="180" cy="980" r="180" fill="rgba(255,255,255,0.08)" />
  <text x="96" y="180" fill="#dbeafe" font-size="34" font-family="Segoe UI, Arial, sans-serif">ACE-Step Prototype</text>
  <text x="96" y="560" fill="#ffffff" font-size="88" font-weight="700" font-family="Segoe UI, Arial, sans-serif">{safe_title}</text>
  <text x="96" y="1040" fill="#bfdbfe" font-size="30" font-family="Segoe UI, Arial, sans-serif">Local cover placeholder for SongsAI-compatible storage contract</text>
</svg>
"""
    target_path.write_text(svg, encoding="utf-8")
    return build_public_media_url("images", file_name)

