# Video-AI — Claude Code 기반 9:16 숏폼 자동 제작 파이프라인

터미널에서 Claude에게 주제만 던지면 **대본 작성 → Veo 영상 생성 → ElevenLabs TTS → ffmpeg 렌더링**까지 자동으로 처리한다.

```
/short 서울 야경
→ jobs/2026-08-18_seoul-night/final.mp4
```

## 새 머신 셋업 (5분)

```bash
git clone https://github.com/chunnho/Video-AI.git
cd Video-AI

# 1. ffmpeg (자막 번인에 libass 필요 — brew 기본 포함)
brew install ffmpeg

# 2. Python 의존성
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. API 키
cp .env.example .env
# .env 열어서 GEMINI_API_KEY, ELEVENLABS_API_KEY 채우기

# 4. 연결 확인 (키·쿼터·모델 검증)
python pipeline/doctor.py
```

그 다음 `claude` 실행 후:

```
/short 주제 또는 장소
```

## 동작 구조

```
Claude (판단)                     pipeline/ (결정론적 실행)
─────────────                     ──────────────────────────
대본·씬 분할 작성        →        job.json 생성
Veo 영어 프롬프트 작성   →        run.py: tts → veo → render
blocked 씬 프롬프트 수정 ←        상태를 job.json에 기록
```

- **`job.json`이 진실 원천(상태머신)**: 씬별 `pending|running|done|failed|blocked`
- **`run.py`는 멱등**: `done`인 씬은 건너뛰므로 재시도 = 그냥 다시 실행
- 429/5xx → 지수 백오프 자동 재시도, 안전필터 거부 → `blocked`로 멈추고 Claude가 프롬프트 리라이트

## 디렉터리

```
pipeline/
├── config.py    # env·상수
├── doctor.py    # 셋업 검증 (키, ffmpeg, 모델)
├── tts.py       # ElevenLabs 나레이션 → mp3 + 길이 측정
├── veo.py       # Veo 씬 생성 (폴링 + 재시도 + 안전필터 분류)
├── render.py    # 트림/오디오 교체/자막/concat → final.mp4
└── run.py       # job.json 오케스트레이터 (멱등)
jobs/
└── <날짜>_<슬러그>/
    ├── job.json
    ├── audio/  scenes/  final.mp4
```

## 수동 실행

```bash
python pipeline/run.py jobs/2026-08-18_seoul-night          # 전체 (이어서 실행)
python pipeline/run.py jobs/... --only-scene 3              # 특정 씬만
python pipeline/render.py jobs/...                          # 렌더만 다시
```

## 비용 팁

- 초안은 `veo-3.1-fast-generate-preview` + 720p, 확정본만 고품질 모델로 재생성 (job.json의 `model` 필드)
- Veo 생성물은 서버에서 **약 2일 후 만료** — 파이프라인이 즉시 로컬 다운로드함
- 모든 Veo 결과물에는 SynthID 워터마크가 포함됨
