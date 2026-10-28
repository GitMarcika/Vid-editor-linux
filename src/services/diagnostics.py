import platform
import sys

from src.services.ffmpeg_export import find_ffmpeg
from src.services.media_info import find_ffprobe
from src.utils.app_paths import (
    application_base_dir,
    log_dir,
    settings_file_path,
    user_data_dir,
)


def build_diagnostics_report() -> str:
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
        f"FFmpeg: {find_ffmpeg() or 'NOT FOUND'}",
        f"FFprobe: {find_ffprobe() or 'NOT FOUND'}",
    ]
    return "\n".join(lines)
