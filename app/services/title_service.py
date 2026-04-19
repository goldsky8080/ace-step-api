from __future__ import annotations

from app.schemas.music import CreateMusicRequest


def build_music_title(payload: CreateMusicRequest) -> str:
    if payload.title and payload.title.strip():
        return payload.title.strip()

    source = payload.prompt or payload.stylePrompt or payload.lyrics
    compact = " ".join(source.split()).strip()
    if not compact:
        return "ACE-Step Prototype Track"
    if len(compact) <= 48:
        return compact
    return f"{compact[:45].rstrip()}..."

