"""셋업 검증: ffmpeg, API 키, 사용 가능한 Veo 모델, ElevenLabs 보이스."""

import shutil
import sys

import config


def check(label: str, ok: bool, detail: str = "") -> bool:
    print(f"  {'✓' if ok else '✗'} {label}" + (f" — {detail}" if detail else ""))
    return ok


def main() -> None:
    print("[doctor] 환경 점검\n")
    ok = True

    ok &= check("ffmpeg", shutil.which("ffmpeg") is not None, "brew install ffmpeg")
    ok &= check("ffprobe", shutil.which("ffprobe") is not None)
    ok &= check("GEMINI_API_KEY", bool(config.GEMINI_API_KEY))
    ok &= check("ELEVENLABS_API_KEY", bool(config.ELEVENLABS_API_KEY))
    ok &= check("ELEVENLABS_VOICE_ID", bool(config.ELEVENLABS_VOICE_ID),
                "" if config.ELEVENLABS_VOICE_ID else "없으면 job.json마다 voice_id 필요")

    if config.GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            veo_models = [m.name for m in client.models.list() if "veo" in m.name.lower()]
            ok &= check("Gemini API 연결", True)
            print(f"    사용 가능한 Veo 모델: {veo_models or '없음(키 권한 확인)'}")
            configured = f"models/{config.VEO_MODEL}"
            if veo_models and configured not in veo_models:
                print(f"    ⚠ 설정된 VEO_MODEL({config.VEO_MODEL})이 목록에 없음 — .env에서 조정 필요")
        except Exception as e:  # noqa: BLE001
            ok &= check("Gemini API 연결", False, str(e)[:200])

    if config.ELEVENLABS_API_KEY:
        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
            voices = client.voices.get_all().voices
            ok &= check("ElevenLabs API 연결", True, f"보이스 {len(voices)}개")
            if config.ELEVENLABS_VOICE_ID:
                found = any(v.voice_id == config.ELEVENLABS_VOICE_ID for v in voices)
                ok &= check("기본 보이스 존재", found, config.ELEVENLABS_VOICE_ID)
        except Exception as e:  # noqa: BLE001
            ok &= check("ElevenLabs API 연결", False, str(e)[:200])

    print(f"\n[doctor] {'모든 점검 통과 — /short 로 시작하세요' if ok else '실패 항목을 해결하세요'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
