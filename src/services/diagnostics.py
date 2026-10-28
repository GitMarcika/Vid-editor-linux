import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional

from src.services.ffmpeg_export import find_ffmpeg
from src.services.media_info import find_ffprobe
from src.utils.app_paths import (
    application_base_dir,
    log_dir,
    settings_file_path,
    user_data_dir,
)


def _first_version_line(path: Optional[str]) -> str:
    if not path:
        return "NOT FOUND"

    try:
        completed = subprocess.run(
            [path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"ERROR: {exc}"

    lines = completed.stdout.splitlines()
    if completed.returncode != 0:
        return f"ERROR: exit {completed.returncode}"
    return lines[0] if lines else "version unavailable"


def _ffmpeg_has_filter(path: Optional[str], filter_name: str) -> str:
    if not path:
        return "no"

    try:
        completed = subprocess.run(
            [path, "-hide_banner", "-filters"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return "error"

    if completed.returncode != 0:
        return "error"

    found = any(
        len(line.split()) >= 2 and line.split()[1] == filter_name
        for line in completed.stdout.splitlines()
    )
    return "yes" if found else "no"


def _ffmpeg_has_libx264(path: Optional[str]) -> str:
    if not path:
        return "no"

    try:
        completed = subprocess.run(
            [path, "-hide_banner", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return "error"

    if completed.returncode != 0:
        return "error"
    return "yes" if "libx264" in completed.stdout else "no"


def build_diagnostics_report() -> str:
    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe()

    lines = [
        "Vid Editor diagnostics",
        "======================",
        f"Platform: {platform.platform()}",
        f"Python: {sys.version.split()[0]}",
        f"Frozen build: {bool(getattr(sys, 'frozen', False))}",
        f"Executable: {sys.executable}",
        f"Application dir: {application_base_dir()}",
        f"User data dir: {user_data_dir()}",
        f"Settings file: {settings_file_path()}",
        f"Log dir: {log_dir()}",
        f"FFmpeg path: {ffmpeg or 'NOT FOUND'}",
        f"FFmpeg version: {_first_version_line(ffmpeg)}",
        f"FFmpeg libx264: {_ffmpeg_has_libx264(ffmpeg)}",
        f"FFmpeg ASS/libass: {_ffmpeg_has_filter(ffmpeg, 'ass')}",
        f"FFprobe path: {ffprobe or 'NOT FOUND'}",
        f"FFprobe version: {_first_version_line(ffprobe)}",
    ]
    return "\n".join(lines)
