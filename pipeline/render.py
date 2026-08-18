"""씬 클립 + 나레이션 + 자막 → 최종 9:16 mp4.

씬마다:
  - 클립을 나레이션 길이에 맞춤 (김: 트림 / 짧음: 마지막 프레임 홀드)
  - Veo 원본 오디오 제거 후 TTS 교체 (keep_ambience=true면 -18dB로 깔아줌)
그다음 전체 concat + SRT 자막 번인.
"""

import json
import subprocess
from pathlib import Path

import config
from tts import probe_duration


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 실패: {' '.join(cmd)}\n{result.stderr[-2000:]}")


def _format_srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def render_scene(scene: dict, job_dir: Path, keep_ambience: bool) -> Path:
    """개별 씬을 나레이션 길이에 맞춰 렌더한 mp4 경로를 반환한다."""
    video = job_dir / scene["video"]
    audio = job_dir / scene["audio"]
    out = job_dir / "scenes" / f"scene_{scene['idx']:02}_final.mp4"
    duration = scene["duration"] + 0.3  # 나레이션 뒤 여백

    video_len = probe_duration(video)
    pad = max(0.0, duration - video_len)
    vf = (
        f"scale={config.WIDTH}:{config.HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={config.WIDTH}:{config.HEIGHT},fps={config.FPS}"
    )
    if pad > 0:
        vf += f",tpad=stop_mode=clone:stop_duration={pad:.3f}"

    cmd = ["ffmpeg", "-y", "-i", str(video), "-i", str(audio)]
    if keep_ambience:
        audio_filter = "[0:a]volume=-18dB[amb];[1:a][amb]amix=inputs=2:duration=first[aout]"
        cmd += ["-filter_complex", f"[0:v]{vf}[vout];{audio_filter}",
                "-map", "[vout]", "-map", "[aout]"]
    else:
        cmd += ["-vf", vf, "-map", "0:v", "-map", "1:a"]
    cmd += ["-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(out)]
    _run(cmd)
    return out


def write_srt(scenes: list[dict], out_path: Path) -> None:
    cursor = 0.0
    lines = []
    for i, scene in enumerate(scenes, start=1):
        end = cursor + scene["duration"]
        lines.append(f"{i}\n{_format_srt_time(cursor)} --> {_format_srt_time(end)}\n{scene['narration']}\n")
        cursor = end + 0.3
    out_path.write_text("\n".join(lines), encoding="utf-8")


def render(job_dir: Path, burn_subs: bool = True) -> Path:
    job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    scenes = sorted(job["scenes"], key=lambda s: s["idx"])
    not_done = [s["idx"] for s in scenes if s["status"] != "done"]
    if not_done:
        raise SystemExit(f"[render] 아직 done이 아닌 씬이 있습니다: {not_done}")

    keep_ambience = job.get("keep_ambience", False)
    clips = [render_scene(s, job_dir, keep_ambience) for s in scenes]

    concat_list = job_dir / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8"
    )
    final = job_dir / "final.mp4"

    if burn_subs:
        srt = job_dir / "subs.srt"
        write_srt(scenes, srt)
        style = "FontName=AppleSDGothicNeo,FontSize=13,Bold=1,PrimaryColour=&HFFFFFF," \
                "OutlineColour=&H80000000,Outline=2,MarginV=60"
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
              "-vf", f"subtitles={srt}:force_style='{style}'",
              "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
              "-c:a", "copy", str(final)])
    else:
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
              "-c", "copy", str(final)])

    print(f"[render] 완료: {final} ({probe_duration(final):.1f}s)")
    return final


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        sys.exit("usage: python pipeline/render.py jobs/<dir> [--no-subs]")
    render(Path(sys.argv[1]), burn_subs="--no-subs" not in sys.argv)
