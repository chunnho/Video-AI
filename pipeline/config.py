"""환경 변수와 공용 상수. 모든 파이프라인 모듈이 여기서 설정을 읽는다."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

VEO_MODEL = os.getenv("VEO_MODEL", "veo-3.1-fast-generate-preview")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

VEO_MAX_RETRY = 4          # 429/5xx 재시도 횟수
VEO_POLL_INTERVAL = 10     # 폴링 주기(초)
VEO_POLL_TIMEOUT = 600     # 씬 하나 최대 대기(초)

# 씬 렌더링 기본값
FPS = 30
WIDTH, HEIGHT = 720, 1280  # 9:16


def require(*names: str) -> None:
    """필수 env가 비어 있으면 즉시 종료한다."""
    missing = [n for n in names if not globals().get(n)]
    if missing:
        sys.exit(f"[config] .env에 다음 키가 필요합니다: {', '.join(missing)}")
