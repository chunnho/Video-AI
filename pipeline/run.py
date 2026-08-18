"""job.json 오케스트레이터 (멱등).

씬별로 TTS → Veo → 상태 기록을 수행하고, 모두 done이면 렌더링한다.
done인 씬은 건너뛰므로 재시도는 그냥 이 스크립트를 다시 실행하면 된다.

usage:
  python pipeline/run.py jobs/<dir>                 # 전체 실행/재개
  python pipeline/run.py jobs/<dir> --only-scene 3  # 특정 씬만
  python pipeline/run.py jobs/<dir> --no-render     # 씬 생성까지만
"""

import argparse
import json
import sys
from pathlib import Path

import render
import tts
import veo


def load_job(job_dir: Path) -> dict:
    path = job_dir / "job.json"
    if not path.exists():
        sys.exit(f"[run] {path} 이 없습니다.")
    return json.loads(path.read_text(encoding="utf-8"))


def save_job(job_dir: Path, job: dict) -> None:
    (job_dir / "job.json").write_text(
        json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def process_scene(scene: dict, job: dict, job_dir: Path) -> None:
    idx = scene["idx"]

    # 1) TTS — 이미 생성된 오디오는 재사용
    if not scene.get("audio") or not (job_dir / scene["audio"]).exists():
        print(f"[scene {idx}] TTS 생성 중...")
        audio_rel = f"audio/scene_{idx:02}.mp3"
        duration = tts.synthesize(
            scene["narration"], job_dir / audio_rel,
            voice_id=scene.get("voice_id") or job.get("voice_id"),
        )
        scene["audio"], scene["duration"] = audio_rel, round(duration, 2)
        save_job(job_dir, job)
        print(f"[scene {idx}] 나레이션 {duration:.2f}s")
        if duration > 7.8:
            print(f"[scene {idx}] ⚠ 나레이션이 {duration:.1f}s — 8초 클립보다 김. "
                  f"마지막 프레임 홀드로 채워지니 나레이션 축약을 권장")

    # 2) Veo
    print(f"[scene {idx}] Veo 생성 중... ({job.get('model') or '기본 모델'})")
    scene["status"] = "running"
    scene["attempts"] = scene.get("attempts", 0) + 1
    save_job(job_dir, job)

    video_rel = f"scenes/scene_{idx:02}.mp4"
    status, detail = veo.generate(
        scene["veo_prompt"], job_dir / video_rel,
        model=job.get("model"),
        resolution=job.get("resolution", "720p"),
    )
    if status == "done":
        scene.update(status="done", video=video_rel, last_error=None)
        print(f"[scene {idx}] ✓ 완료")
    else:
        scene.update(status=status, last_error=detail)
        print(f"[scene {idx}] ✗ {status}: {detail[:300]}")
    save_job(job_dir, job)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--only-scene", type=int, default=None)
    parser.add_argument("--no-render", action="store_true")
    args = parser.parse_args()

    job = load_job(args.job_dir)
    scenes = sorted(job["scenes"], key=lambda s: s["idx"])

    for scene in scenes:
        if args.only_scene is not None and scene["idx"] != args.only_scene:
            continue
        if scene["status"] == "done":
            print(f"[scene {scene['idx']}] 이미 완료 — 건너뜀")
            continue
        if scene["status"] == "blocked" and args.only_scene is None:
            print(f"[scene {scene['idx']}] blocked — 프롬프트 수정 후 status를 pending으로 바꿔주세요")
            continue
        process_scene(scene, job, args.job_dir)

    done = [s for s in scenes if s["status"] == "done"]
    print(f"\n[run] 씬 상태: {len(done)}/{len(scenes)} done")
    for s in scenes:
        mark = {"done": "✓", "blocked": "⛔", "failed": "✗"}.get(s["status"], "·")
        print(f"  {mark} scene {s['idx']}: {s['status']}"
              + (f" — {s['last_error'][:120]}" if s.get("last_error") else ""))

    if len(done) == len(scenes) and not args.no_render:
        render.render(args.job_dir, burn_subs=job.get("burn_subs", True))
    elif len(done) < len(scenes):
        sys.exit(1)


if __name__ == "__main__":
    main()
