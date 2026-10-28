import os
import sys
from pathlib import Path


def application_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def user_data_dir() -> Path:
    base_dir = application_base_dir()
    portable_requested = (
        os.environ.get("VIDEDITOR_PORTABLE", "").strip() == "1"
        or (base_dir / "portable.flag").is_file()
    )
    if portable_requested:
        return base_dir / "user_data"

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "VidEditor"

    return Path.home() / ".vid-editor"


def settings_file_path() -> Path:
    override = os.environ.get("VIDEDITOR_SETTINGS_FILE")
    if override:
        return Path(override)
    return user_data_dir() / "settings.json"


def log_dir() -> Path:
    return user_data_dir() / "logs"
