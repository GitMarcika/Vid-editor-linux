import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from src.project import empty_project, load_project, save_project
from src.services.assembly_export import build_assembly_export_arguments
from src.services.ffmpeg_export import build_export_arguments, find_ffmpeg
from src.services.linux_screen_capture import (
    check_ffmpeg_x11grab,
    check_gnome_screencast_area,
    detect_linux_session,
)
from src.services.media_info import (
    extract_thumbnail_png,
    find_ffprobe,
    probe_video_info,
)
from src.settings import AppSettings
from src.utils.app_paths import application_base_dir, user_data_dir
from src.utils.media_paths import media_reference_basename


Result = Tuple[str, str, str]


def _run_command(
    command: List[str],
    timeout: int = 60,
) -> Tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)

    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    details = (stderr or stdout).strip()
    if completed.returncode != 0:
        return False, details[-4000:] or f"exit {completed.returncode}"
    return True, details[-2000:]


def _make_overlay() -> dict:
    return {
        "id": "acceptance-overlay",
        "text": "Acceptance ő",
        "start_ms": 250,
        "end_ms": 1750,
        "x_norm": 0.12,
        "y_norm": 0.18,
        "font_family": "DejaVu Sans",
        "font_size": 28,
        "text_color": "#ffffff",
        "background_enabled": True,
        "background_color": "#000000",
        "background_opacity": 170,
        "background_padding": 8,
        "outline_enabled": True,
        "outline_color": "#000000",
        "outline_width": 2,
        "shadow_enabled": True,
        "shadow_color": "#000000",
        "shadow_opacity": 160,
        "shadow_blur": 8,
        "shadow_offset_x": 3,
        "shadow_offset_y": 3,
    }


def run_internal_acceptance(main_window) -> Tuple[bool, str]:
    results: List[Result] = []

    def record(
        status: str,
        name: str,
        detail: str = "",
    ) -> None:
        results.append((status, name, detail))

    def check(name: str, condition: bool, detail: str = "") -> bool:
        record("PASS" if condition else "FAIL", name, detail)
        return condition

    base = application_base_dir()
    portable = (base / "portable.flag").is_file()
    frozen = bool(getattr(sys, "frozen", False))

    check("Frozen executable", frozen, str(sys.executable))
    check("portable.flag present", portable, str(base / "portable.flag"))
    check(
        "Portable user_data path",
        user_data_dir().resolve() == (base / "user_data").resolve(),
        str(user_data_dir()),
    )
    runtime_root = (base / "user_data" / "runtime").resolve()
    expected_runtime_env = {
        "XDG_CACHE_HOME": runtime_root / "cache",
        "XDG_CONFIG_HOME": runtime_root / "config",
        "XDG_DATA_HOME": runtime_root / "data",
        "XDG_STATE_HOME": runtime_root / "state",
        "TMPDIR": runtime_root / "tmp",
        "MESA_SHADER_CACHE_DIR": runtime_root / "cache" / "mesa",
    }
    for key, expected in expected_runtime_env.items():
        value = os.environ.get(key, "")
        check(
            f"Portable runtime env {key}",
            bool(value) and Path(value).resolve() == expected.resolve(),
            value or "not set",
        )


    try:
        tab_names = [
            main_window.tabs.tabText(index)
            for index in range(main_window.tabs.count())
        ]
        check(
            "Main window has three application tabs",
            tab_names == ["Raw Cutter", "Assembly", "Screen Recorder"],
            ", ".join(tab_names),
        )
    except Exception as exc:
        record("FAIL", "Main window/tab construction", str(exc))

    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe()
    expected_ffmpeg = base / "tools" / "ffmpeg" / "ffmpeg"
    expected_ffprobe = base / "tools" / "ffmpeg" / "ffprobe"

    check(
        "Application-local FFmpeg resolved",
        bool(ffmpeg) and Path(ffmpeg).resolve() == expected_ffmpeg.resolve(),
        str(ffmpeg or "NOT FOUND"),
    )
    check(
        "Application-local FFprobe resolved",
        bool(ffprobe) and Path(ffprobe).resolve() == expected_ffprobe.resolve(),
        str(ffprobe or "NOT FOUND"),
    )

    data_dir = user_data_dir()
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="acceptance space ő-",
            dir=str(data_dir),
        ) as temp_name:
            temp = Path(temp_name)
            check(
                "Portable user_data is writable",
                temp.is_dir(),
                str(temp),
            )

            old_settings = os.environ.get("VIDEDITOR_SETTINGS_FILE")
            settings_path = temp / "settings acceptance ő.json"
            os.environ["VIDEDITOR_SETTINGS_FILE"] = str(settings_path)
            try:
                first = AppSettings()
                marker = str(temp / "input könyvtár")
                first.set_input_dir(marker)
                second = AppSettings()
                check(
                    "JSON settings write/read roundtrip",
                    second.input_dir() == marker,
                    str(settings_path),
                )
            except Exception as exc:
                record("FAIL", "JSON settings write/read roundtrip", str(exc))
            finally:
                if old_settings is None:
                    os.environ.pop("VIDEDITOR_SETTINGS_FILE", None)
                else:
                    os.environ["VIDEDITOR_SETTINGS_FILE"] = old_settings

            try:
                project = empty_project()
                project["raw_cutter"]["acceptance_marker"] = "árvíztűrő"
                project_path = temp / "project acceptance ő.vedproj"
                save_project(project_path, project)
                loaded = load_project(project_path)
                check(
                    ".vedproj save/load roundtrip",
                    loaded == project,
                    str(project_path),
                )
            except Exception as exc:
                record("FAIL", ".vedproj save/load roundtrip", str(exc))

            check(
                "Windows media basename on Linux",
                media_reference_basename(
                    r"C:\\videos\\scene\\clip.mp4"
                ) == "clip.mp4",
            )

            if ffmpeg and ffprobe:
                _run_media_acceptance(
                    Path(ffmpeg),
                    temp,
                    record,
                    check,
                )
            else:
                record(
                    "FAIL",
                    "Media acceptance",
                    "FFmpeg/FFprobe unavailable.",
                )
    except Exception as exc:
        record("FAIL", "Acceptance workspace", str(exc))

    session = detect_linux_session()
    if session.is_x11:
        ok, detail = check_ffmpeg_x11grab(ffmpeg)
        check("X11 recorder backend capability", ok, detail)
    elif session.is_wayland:
        ok, detail = check_gnome_screencast_area(session.gdbus_path)
        check("GNOME Wayland recorder backend capability", ok, detail)
    else:
        record(
            "FAIL",
            "Linux recorder session detection",
            "Neither X11 nor Wayland was detected.",
        )

    failures = [item for item in results if item[0] == "FAIL"]
    lines = [
        "Vid Editor internal RHEL8 acceptance probe",
        "==========================================",
        f"Executable: {sys.executable}",
        f"Application dir: {base}",
        f"Session: {session.kind}",
        "",
    ]
    for status, name, detail in results:
        suffix = f" | {detail}" if detail else ""
        lines.append(f"[{status}] {name}{suffix}")

    lines.extend(
        [
            "",
            f"PASS: {sum(1 for item in results if item[0] == 'PASS')}",
            f"FAIL: {len(failures)}",
            f"RESULT: {'FAIL' if failures else 'PASS'}",
        ]
    )
    return not failures, "\n".join(lines) + "\n"


def _run_media_acceptance(
    ffmpeg: Path,
    temp: Path,
    record: Callable[[str, str, str], None],
    check: Callable[[str, bool, str], bool],
) -> None:
    first = temp / "source one ő.mp4"
    second = temp / "source two no audio.mp4"

    ok, detail = _run_command(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=640x360:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-t",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(first),
        ]
    )
    if not check("Synthetic H.264/AAC source generation", ok, detail):
        return

    thumbnail = extract_thumbnail_png(first)
    check(
        "FFmpeg thumbnail extraction",
        bool(thumbnail) and thumbnail.startswith(b"\x89PNG"),
        f"{len(thumbnail or b'')} bytes",
    )

    raw_output = temp / "raw crop output ő.mp4"
    try:
        raw_args = build_export_arguments(
            first,
            raw_output,
            500,
            1500,
            (100, 60, 320, 240),
        )
        ok, detail = _run_command([str(ffmpeg)] + raw_args)
        if check("Raw Cutter service export", ok, detail):
            info = probe_video_info(raw_output)
            check(
                "Raw Cutter output geometry",
                (info.width, info.height) == (320, 240),
                f"{info.width}x{info.height}, {info.duration_ms} ms",
            )
            check(
                "Raw Cutter output duration",
                800 <= info.duration_ms <= 1200,
                f"{info.duration_ms} ms",
            )
    except Exception as exc:
        record("FAIL", "Raw Cutter service export", str(exc))

    ok, detail = _run_command(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x240:rate=24",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(second),
        ]
    )
    if not check("Second no-audio source generation", ok, detail):
        return

    assembly_output = temp / "assembly output ő.mp4"
    work_dir = temp / "assembly work"
    clips = [
        {"id": "a", "path": str(first), "duration_ms": 1000},
        {"id": "b", "path": str(second), "duration_ms": 1000},
    ]

    try:
        args, expected_ms, width, height, fps = (
            build_assembly_export_arguments(
                clips,
                [_make_overlay()],
                assembly_output,
                work_dir,
            )
        )
        check(
            "Assembly service selected first-clip canvas",
            (width, height) == (640, 360),
            f"{width}x{height} @ {fps:.3f} fps",
        )
        check(
            "Assembly service timeline duration",
            expected_ms == 2000,
            f"{expected_ms} ms",
        )
        ok, detail = _run_command([str(ffmpeg)] + args, timeout=90)
        if check("Assembly service render with ASS overlay", ok, detail):
            info = probe_video_info(assembly_output)
            check(
                "Assembly output geometry/audio",
                (
                    (info.width, info.height) == (640, 360)
                    and info.has_audio
                ),
                (
                    f"{info.width}x{info.height}, audio={info.has_audio}, "
                    f"{info.duration_ms} ms"
                ),
            )
            check(
                "Assembly output duration",
                1800 <= info.duration_ms <= 2200,
                f"{info.duration_ms} ms",
            )
    except Exception as exc:
        record(
            "FAIL",
            "Assembly service render with ASS overlay",
            str(exc),
        )
