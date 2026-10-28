import os
import shutil
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.services.ffmpeg_export import find_ffmpeg
from src.utils.app_paths import application_base_dir


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    fps: float
    has_audio: bool
    duration_ms: int = 0


def _creation_flags() -> int:
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        return subprocess.CREATE_NO_WINDOW
    return 0


def find_ffprobe() -> Optional[str]:
    executable = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    bundled = application_base_dir() / "tools" / "ffmpeg" / executable
    if bundled.is_file() and (os.name == "nt" or os.access(bundled, os.X_OK)):
        return str(bundled)

    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path:
        sibling_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
        sibling = Path(ffmpeg_path).with_name(sibling_name)
        if sibling.is_file():
            return str(sibling)

    return shutil.which("ffprobe")


def probe_duration_ms(path: Path) -> int:
    ffprobe = find_ffprobe()
    if not ffprobe:
        raise RuntimeError(
            "FFprobe was not found. Install FFmpeg/FFprobe or place both "
            "executables in tools/ffmpeg."
        )

    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
        creationflags=_creation_flags(),
    )

    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error or f"Could not probe {path.name}.")

    value = completed.stdout.decode("utf-8", errors="replace").strip()
    try:
        seconds = float(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid duration returned for {path.name}.") from exc

    return max(0, round(seconds * 1000))


def extract_thumbnail_png(
    path: Path,
    width: int = 160,
    height: int = 90,
) -> Optional[bytes]:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return None

    filter_expr = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    )

    completed = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            "0.250",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            filter_expr,
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=20,
        creationflags=_creation_flags(),
    )

    if completed.returncode != 0 or not completed.stdout:
        return None
    return bytes(completed.stdout)

def probe_video_info(path: Path) -> VideoInfo:
    ffprobe = find_ffprobe()
    if not ffprobe:
        raise RuntimeError(
            "FFprobe was not found. Install FFmpeg/FFprobe or place both "
            "executables in tools/ffmpeg."
        )

    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,width,height,avg_frame_rate:format=duration",
            "-of",
            "json",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
        creationflags=_creation_flags(),
    )

    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error or f"Could not probe {path.name}.")

    try:
        payload = json.loads(
            completed.stdout.decode("utf-8", errors="replace")
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid FFprobe response for {path.name}."
        ) from exc

    video_stream = None
    has_audio = False
    for stream in payload.get("streams", []):
        if stream.get("codec_type") == "video" and video_stream is None:
            video_stream = stream
        elif stream.get("codec_type") == "audio":
            has_audio = True

    if video_stream is None:
        raise RuntimeError(f"No video stream found in {path.name}.")

    width = max(1, int(video_stream.get("width") or 0))
    height = max(1, int(video_stream.get("height") or 0))

    fps_text = str(video_stream.get("avg_frame_rate") or "0/1")
    try:
        numerator_text, denominator_text = fps_text.split("/", 1)
        numerator = float(numerator_text)
        denominator = float(denominator_text)
        fps = numerator / denominator if denominator else 0.0
    except (ValueError, ZeroDivisionError):
        fps = 0.0

    if fps <= 0:
        fps = 30.0

    duration_ms = 0
    try:
        duration_ms = max(
            0,
            round(float(payload.get("format", {}).get("duration", 0)) * 1000),
        )
    except (TypeError, ValueError):
        duration_ms = 0

    return VideoInfo(
        width=width,
        height=height,
        fps=fps,
        has_audio=has_audio,
        duration_ms=duration_ms,
    )

