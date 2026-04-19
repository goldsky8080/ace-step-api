# ACE-Step Prototype 작업 기록

기준일: 2026-04-19

## 목적

- `D:\aceStep`를 독립 `ACE-Step API` 프로토타입 서버로 구성
- 테스트 단계에서는 이 프로젝트 안에서 간단한 UI로 직접 생성 요청
- 추후 최종 목표는 `songsai-api`가 `provider=ace_step` 분기 시 이 서버를 호출하도록 연결
- DB 저장은 `ACE-Step` 서버가 직접 수행
- 저장 형식은 SongsAI 기존 읽기 구조와 호환되도록 유지

## 참고한 기준 문서

- `D:\songsai-music-pc\docs\16_ACE-Step_독립저장형_아키텍처_설계.md`
- `D:\songsai-music-pc\docs\17_ACE-Step_DB_저장_규칙_계약서.md`

핵심 해석:

- `provider=ace_step`는 독립 서비스로 분리
- `ACE-Step` 서버가 생성, 상태관리, 파일처리, DB 저장까지 담당
- `Music` 저장 형식은 기존 SongsAI 프론트/읽기 API와 호환되어야 함

## 현재 구현된 프로토타입 구조

```text
D:\aceStep
├─ app
│  ├─ api
│  │  ├─ health.py
│  │  ├─ music.py
│  │  └─ web.py
│  ├─ repositories
│  │  └─ music_repository.py
│  ├─ schemas
│  │  └─ music.py
│  ├─ services
│  │  ├─ ace_client.py
│  │  ├─ music_service.py
│  │  ├─ storage_service.py
│  │  └─ title_service.py
│  ├─ static
│  │  └─ app.css
│  ├─ templates
│  │  └─ index.html
│  ├─ config.py
│  ├─ db.py
│  └─ main.py
├─ storage
│  ├─ audio
│  ├─ images
│  └─ metadata
├─ .env.example
├─ .gitignore
├─ README.md
└─ requirements.txt
```

## 사용 기술 스택

- FastAPI
- SQLAlchemy Core
- PostgreSQL
- Jinja2 테스트 UI
- 로컬 파일 저장소
- ACE-Step REST API 연동

## 현재 환경 기준 설정

```env
APP_NAME="ACE-Step API Prototype"
APP_ENV="development"
APP_HOST="127.0.0.1"
APP_PORT="8200"
PUBLIC_BASE_URL="http://127.0.0.1:8200"

DATABASE_URL="postgresql://postgres:1469@localhost:5432/music_platform?schema=songsai_api"
DB_SCHEMA="songsai_api"

ACESTEP_BASE_URL="http://127.0.0.1:8001"
ACESTEP_API_KEY=""
ACESTEP_REQUEST_TIMEOUT_SECONDS="600"
ACESTEP_POLL_TIMEOUT_SECONDS="120"
POLL_INTERVAL_SECONDS="10"
MAX_POLL_ATTEMPTS="90"
PROTOTYPE_USER_ID=""
```

주의:

- 내부 SQLAlchemy 연결에서는 Prisma 스타일 `?schema=` 쿼리스트링을 제거하고 접속
- 스키마 이름은 별도로 `DB_SCHEMA`에서 사용

## 구현된 기능

### 1. 테스트 UI

- `/` 에서 단일 페이지 테스트 화면 제공
- 입력 필드:
  - `SongsAI User ID`
  - `title`
  - `stylePrompt`
  - `lyrics`
  - `prompt`
  - `model`
  - `duration`
  - `vocalLanguage`
  - `thinking`

### 2. 최근 사용자 추천

- `GET /api/v1/music/prototype-users`
- 최근 `songsai_api."User"` 목록을 내려줌
- 테스트 화면에서 `User.id` 추천 목록으로 선택 가능
- 선택 시 이메일/이름 표시

### 3. 음악 생성 API

- `POST /api/v1/music`
- 생성 요청을 DB에 `queued` 상태로 저장
- `GenerationJob`도 함께 생성
- 백그라운드에서 `ACE-Step` API 호출

### 4. 읽기 API

- `GET /api/v1/music`
- `GET /api/v1/music/{id}`
- `GET /api/v1/music/{id}/download`

### 5. 헬스체크

- `GET /health`
- DB 연결 여부
- ACE-Step API 연결 여부 확인

## SongsAI 저장 계약 반영 사항

`Music` 저장 시 다음 규칙을 맞추도록 구현함.

- `provider = "ACE_STEP"`
- `status = queued / processing / completed / failed`
- `providerTaskId` 저장
- `title`, `lyrics`, `stylePrompt` 저장
- `completed`는 실제 `mp3Url` 확보 후만 기록
- 실패 시 `errorMessage` 저장

## 실제 확인된 동작 상태

### 확인 완료

- Python 가상환경 생성 완료
- 의존성 설치 완료
- FastAPI 앱 import 성공
- PostgreSQL 연결 성공
- `songsai_api` 스키마 접근 성공
- 최근 사용자 목록 조회 성공
- 프로토타입 서버 기동 성공
- `ACE-Step-1.5` API 서버 `http://127.0.0.1:8001/health` 응답 성공

### 수정한 문제들

#### 1. `userId` 외래키 오류

증상:

- 존재하지 않는 `User.id`로 `Music` insert 시 외래키 위반

조치:

- 생성 전 `songsai_api."User"` 존재 여부 검사 추가
- 잘못된 `userId`는 `500`이 아니라 `400`으로 반환하도록 수정

#### 2. DB URL의 `schema` 파라미터 문제

증상:

- `psycopg` 연결 시 `invalid connection option "schema"`

조치:

- SQLAlchemy 연결용 URL에서 `?schema=` 제거
- 스키마명은 `DB_SCHEMA`로 따로 사용

#### 3. 초기 `ACE-Step` 연결 실패

증상:

- `[WinError 10061] 대상 컴퓨터에서 연결을 거부했으므로 연결하지 못했습니다`

원인:

- `ACE-Step-1.5` API 서버 미기동

조치:

- `uv run acestep-api`로 별도 서버 실행 필요 확인

#### 4. 초기 생성 타임아웃

증상:

- 화면에서 `timed out`
- `providerTaskId` 미기록

원인:

- `release_task` 응답이 모델 초기화 때문에 오래 걸림

조치:

- `ACESTEP_REQUEST_TIMEOUT_SECONDS=600`
- `ACESTEP_POLL_TIMEOUT_SECONDS=120`
- 타임아웃 메시지 명확화

## 현재 가장 중요한 이슈

### GPU / VRAM 문제 의심

`ACE-Step-1.5` 로그에서 확인된 내용:

- `Model generation completed. Decoding latents...`
- `Effective free VRAM before VAE decode: 0.00 GB`
- `Only 0.00 GB free VRAM; auto-enabling CPU VAE decode`
- `Moving VAE to CPU for decode`

해석:

- 생성 자체는 상당 부분 진행됨
- 하지만 VAE decode 단계에서 GPU 메모리 여유가 없음
- 자동으로 CPU decode로 내려가면서 매우 느려짐

가능성:

- 새 그래픽카드 드라이버 미설치 또는 비정상 설치
- CUDA/torch/GPU 인식 문제
- 실제 VRAM 부족
- 다른 프로세스가 GPU 메모리를 점유

## 현재 판단

- `ACE-Step` 서버는 이제 연결됨
- DB 저장 계약을 따르는 프로토타입 서버도 동작함
- 지금 막히는 핵심은 `ACE-Step` 모델 추론/디코드 성능 또는 GPU 인식 상태
- 즉 백엔드 구조 문제보다 실행 환경 문제 비중이 큼

## 다음 확인 권장 순서

### 1. GPU 드라이버 확인

```powershell
nvidia-smi
```

### 2. PyTorch가 CUDA 인식하는지 확인

`ACE-Step-1.5` 폴더에서:

```powershell
uv run python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.device_count()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no gpu')"
```

### 3. 테스트 조건을 더 가볍게 조정

- 더 짧은 duration
- turbo 모델 유지
- 첫 요청은 충분히 오래 대기

## 현재 실행 명령

### ACE-Step 프로토타입 서버

```powershell
cd D:\aceStep
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8200
```

### ACE-Step 실제 모델 API 서버

```powershell
cd D:\ACE-Step-1.5
uv run acestep-api
```

### ACE-Step health 확인

```powershell
Invoke-WebRequest http://127.0.0.1:8001/health -UseBasicParsing
```

### 프로토타입 health 확인

```powershell
Invoke-WebRequest http://127.0.0.1:8200/health -UseBasicParsing
```

## 메모

- 현재 커버 이미지는 MVP 단계라 placeholder SVG 생성
- 실제 음악 생성 완료 시 `storage/audio`에 로컬 파일 저장 후 `mp3Url` 기록
- 향후 `songsai-api`는 `provider=ace_step`일 때 이 서버를 호출하는 분기만 추가하면 되는 구조를 목표로 함
