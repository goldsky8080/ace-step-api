# ACE-Step Prototype

`D:\aceStep`는 ACE-Step wrapper 저장형 응답 서버 프로토타입입니다.

목표:

- 로컬 테스트 화면에서 직접 생성 요청
- ACE-Step API 서버 호출
- 결과를 wrapper가 바로 저장할 수 있는 정규화 응답으로 반환
- 나중에 `songsai-api`에서 `provider=ace_step` 분기용 백엔드로 이식

## Stack

- FastAPI
- Jinja2 test UI
- Local storage for audio and cover assets

## Required Environment

1. ACE-Step API server running
2. Enough local disk space for downloaded outputs

## Quick Start

```powershell
Copy-Item .env.example .env
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8200
```

Then open:

- `http://127.0.0.1:8200/`

## API

- `GET /health`
- `POST /api/v1/music`
- `GET /api/v1/music`
- `GET /api/v1/music/{requestId}`
- `GET /api/v1/music/{requestId}/download`

## Notes

- response contract follows `docs/18_ACE-Step_wrapper저장형_응답계약_및_저장흐름.md`
- `status` transitions follow `queued -> processing -> completed/failed`
- `completed` is returned only after a usable local `mp3Url` exists
- cover images are generated as local SVG placeholders in this MVP
- first `release_task` can be slow during model initialization, so ACE-Step HTTP timeouts are configurable via `.env`
