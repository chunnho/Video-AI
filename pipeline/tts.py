"""ElevenLabs 나레이션 생성 + ffprobe 길이 측정."""

import json
import subprocess
from pathlib import Path

import config


def synthesize(text: str, out_path: Path, voice_id: str | None = None) -> float:
    """나레이션 mp3를 생성하고 실제 길이(초)를 반환한다."""
    config.require("ELEVENLABS_API_KEY")
    voice = voice_id or config.ELEVENLABS_VOICE_ID
    if not voice:
        raise SystemExit("[tts] voice_id가 없습니다. .env의 ELEVENLABS_VOICE_ID 또는 job.json의 voice_id를 설정하세요.")

    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
    audio = client.text_to_speech.convert(
        voice_id=voice,
        model_id=config.ELEVENLABS_MODEL,
        text=text,
        output_format="mp3_44100_128",
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    return probe_duration(out_path)


def probe_duration(path: Path) -> float:
    """미디어 파일의 길이(초)를 반환한다."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        sys.exit("usage: python pipeline/tts.py '나레이션 텍스트' out.mp3")
    duration = synthesize(sys.argv[1], Path(sys.argv[2]))
    print(f"생성 완료: {sys.argv[2]} ({duration:.2f}s)")
