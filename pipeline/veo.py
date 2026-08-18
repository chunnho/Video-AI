"""Veo 영상 생성: 폴링 + 지수 백오프 재시도 + 안전필터 분류.

반환 규약:
  ("done", 파일경로)   — 성공, mp4 다운로드 완료
  ("blocked", 사유)    — 안전필터 거부. 재시도 무의미, 프롬프트 리라이트 필요
  ("failed", 사유)     — 일시 오류. run.py 재실행으로 재시도 가능
"""

import time
from pathlib import Path

import config

SAFETY_MARKERS = ("safety", "rai", "blocked", "prohibited", "violate")


def _is_safety_block(message: str) -> bool:
    lowered = message.lower()
    return any(marker in lowered for marker in SAFETY_MARKERS)


def generate(prompt: str, out_path: Path, model: str | None = None,
             resolution: str = "720p") -> tuple[str, str]:
    config.require("GEMINI_API_KEY")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    model = model or config.VEO_MODEL
    last_error = "unknown"

    for attempt in range(config.VEO_MAX_RETRY):
        if attempt > 0:
            backoff = 2 ** attempt * 5
            print(f"  [veo] 재시도 {attempt}/{config.VEO_MAX_RETRY - 1} ({backoff}s 대기) — {last_error}")
            time.sleep(backoff)
        try:
            operation = client.models.generate_videos(
                model=model,
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16",
                    resolution=resolution,
                ),
            )
            deadline = time.time() + config.VEO_POLL_TIMEOUT
            while not operation.done:
                if time.time() > deadline:
                    raise TimeoutError(f"폴링 {config.VEO_POLL_TIMEOUT}s 초과")
                time.sleep(config.VEO_POLL_INTERVAL)
                operation = client.operations.get(operation)

            if operation.error:
                message = str(operation.error)
                if _is_safety_block(message):
                    return "blocked", message
                last_error = message
                continue

            videos = operation.response.generated_videos
            if not videos:
                # 결과 없이 완료 = 대부분 안전필터가 조용히 걸러낸 경우
                return "blocked", "결과 영상 0개 (안전필터로 필터링된 것으로 추정)"

            out_path.parent.mkdir(parents=True, exist_ok=True)
            client.files.download(file=videos[0].video)
            videos[0].video.save(str(out_path))
            return "done", str(out_path)

        except Exception as e:  # noqa: BLE001 - 네트워크/쿼터 계열은 종류가 많아 일괄 재시도
            message = str(e)
            if _is_safety_block(message):
                return "blocked", message
            last_error = message

    return "failed", last_error


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        sys.exit('usage: python pipeline/veo.py "english prompt" out.mp4')
    status, detail = generate(sys.argv[1], Path(sys.argv[2]))
    print(f"{status}: {detail}")
    sys.exit(0 if status == "done" else 1)
