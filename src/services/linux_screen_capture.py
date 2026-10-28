import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from PySide6.QtCore import QObject, QProcess, QTimer, Signal


GNOME_SCREENCAST_DEST = "org.gnome.Shell.Screencast"
GNOME_SCREENCAST_PATH = "/org/gnome/Shell/Screencast"
GNOME_SCREENCAST_IFACE = "org.gnome.Shell.Screencast"


@dataclass(frozen=True)
class LinuxSessionInfo:
    kind: str
    display: str
    wayland_display: str
    gdbus_path: Optional[str]

    @property
    def is_x11(self) -> bool:
        return self.kind == "x11"

    @property
    def is_wayland(self) -> bool:
        return self.kind == "wayland"


def detect_linux_session(
    env: Optional[Dict[str, str]] = None,
) -> LinuxSessionInfo:
    values = os.environ if env is None else env
    session_type = str(values.get("XDG_SESSION_TYPE", "")).strip().lower()
    display = str(values.get("DISPLAY", "")).strip()
    wayland_display = str(values.get("WAYLAND_DISPLAY", "")).strip()

    if session_type == "wayland" or (
        wayland_display and session_type != "x11"
    ):
        kind = "wayland"
    elif session_type == "x11" or display:
        kind = "x11"
    else:
        kind = "unknown"

    return LinuxSessionInfo(
        kind=kind,
        display=display,
        wayland_display=wayland_display,
        gdbus_path=shutil.which("gdbus"),
    )


def make_even_region(
    x: int,
    y: int,
    width: int,
    height: int,
) -> Tuple[int, int, int, int]:
    width = max(2, int(width) - (int(width) % 2))
    height = max(2, int(height) - (int(height) % 2))
    return int(x), int(y), width, height


def qt_rect_to_x11_region(
    frame_x: int,
    frame_y: int,
    frame_width: int,
    frame_height: int,
    screen_x: int,
    screen_y: int,
    device_pixel_ratio: float,
) -> Tuple[int, int, int, int]:
    ratio = max(0.01, float(device_pixel_ratio))
    local_x = int(frame_x) - int(screen_x)
    local_y = int(frame_y) - int(screen_y)

    physical_screen_x = round(int(screen_x) * ratio)
    physical_screen_y = round(int(screen_y) * ratio)

    return make_even_region(
        physical_screen_x + round(local_x * ratio),
        physical_screen_y + round(local_y * ratio),
        round(int(frame_width) * ratio),
        round(int(frame_height) * ratio),
    )


def build_x11grab_arguments(
    output_path: Path,
    fps: int,
    display: str,
    region: Tuple[int, int, int, int],
) -> List[str]:
    x, y, width, height = make_even_region(*region)
    fps = int(fps)
    if fps <= 0:
        raise ValueError("FPS must be positive.")
    if not display:
        raise ValueError("DISPLAY is not set for the X11 session.")

    return [
        "-hide_banner",
        "-y",
        "-f",
        "x11grab",
        "-framerate",
        str(fps),
        "-draw_mouse",
        "1",
        "-video_size",
        f"{width}x{height}",
        "-i",
        f"{display}+{x},{y}",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-nostats",
        str(output_path),
    ]


def gnome_screencast_start_arguments(
    region: Tuple[int, int, int, int],
    output_webm: Path,
    fps: int,
) -> List[str]:
    x, y, width, height = (
        int(region[0]),
        int(region[1]),
        max(1, int(region[2])),
        max(1, int(region[3])),
    )
    fps = int(fps)
    if fps <= 0:
        raise ValueError("FPS must be positive.")

    options = (
        "{'draw-cursor': <true>, "
        f"'framerate': <{fps}>}}"
    )
    return [
        "call",
        "--session",
        "--dest",
        GNOME_SCREENCAST_DEST,
        "--object-path",
        GNOME_SCREENCAST_PATH,
        "--method",
        f"{GNOME_SCREENCAST_IFACE}.ScreencastArea",
        str(x),
        str(y),
        str(width),
        str(height),
        str(output_webm),
        options,
    ]


def gnome_screencast_stop_arguments() -> List[str]:
    return [
        "call",
        "--session",
        "--dest",
        GNOME_SCREENCAST_DEST,
        "--object-path",
        GNOME_SCREENCAST_PATH,
        "--method",
        f"{GNOME_SCREENCAST_IFACE}.StopScreencast",
    ]


def gnome_screencast_introspect_arguments() -> List[str]:
    return [
        "introspect",
        "--session",
        "--dest",
        GNOME_SCREENCAST_DEST,
        "--object-path",
        GNOME_SCREENCAST_PATH,
    ]


def parse_gdbus_start_result(output: str) -> Tuple[bool, str]:
    match = re.search(
        r"\(\s*(true|false)\s*,\s*['\"]([^'\"]*)['\"]\s*\)",
        str(output),
        flags=re.IGNORECASE,
    )
    if not match:
        return False, ""
    return match.group(1).lower() == "true", match.group(2)


def parse_gdbus_bool_result(output: str) -> bool:
    return bool(
        re.search(
            r"\(\s*true\s*,?\s*\)",
            str(output),
            flags=re.IGNORECASE,
        )
    )


def build_wayland_transcode_arguments(
    source_webm: Path,
    output_path: Path,
    target_size: Optional[Tuple[int, int]] = None,
) -> List[str]:
    args = [
        "-hide_banner",
        "-y",
        "-i",
        str(source_webm),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
    ]

    if target_size is not None:
        _x, _y, target_width, target_height = make_even_region(
            0,
            0,
            int(target_size[0]),
            int(target_size[1]),
        )
        args.extend(["-vf", f"scale={target_width}:{target_height}"])

    args.extend(
        [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        ]
    )

    if output_path.suffix.lower() in (".mp4", ".mov", ".m4v"):
        args.extend(
            [
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
            ]
        )

    args.append(str(output_path))
    return args



def check_gnome_screencast_area(
    gdbus_path: Optional[str],
) -> Tuple[bool, str]:
    if not gdbus_path:
        return False, "gdbus was not found."

    try:
        completed = subprocess.run(
            [gdbus_path] + gnome_screencast_introspect_arguments(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)

    if completed.returncode != 0:
        return False, completed.stdout.strip()[-2000:]

    if "ScreencastArea" not in completed.stdout:
        return False, "GNOME ScreencastArea D-Bus method was not found."

    return True, "GNOME ScreencastArea is available."


def check_ffmpeg_x11grab(ffmpeg_path: Optional[str]) -> Tuple[bool, str]:
    """
    Lightweight X11 readiness check.

    Do not call `ffmpeg -devices` here. On some enterprise/VNC RHEL8
    workstations that compile-time listing can block for many seconds even
    though real x11grab capture works. The actual recording start is the
    authoritative x11grab test and returns useful FFmpeg stderr on failure.
    """
    if not ffmpeg_path:
        return False, "FFmpeg was not found."

    path = Path(ffmpeg_path)
    if not path.is_file():
        return False, f"FFmpeg does not exist: {path}"
    if not os.access(path, os.X_OK):
        return False, f"FFmpeg is not executable: {path}"

    return (
        True,
        "FFmpeg executable is available. "
        "x11grab is validated by the actual recording start.",
    )


class X11RecordingJob(QObject):
    started = Signal()
    statusChanged = Signal(str)
    finished = Signal(bool, str)

    def __init__(
        self,
        ffmpeg_path: str,
        arguments: List[str],
        partial_path: Path,
        final_path: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._partial_path = Path(partial_path)
        self._final_path = Path(final_path)
        self._stop_requested = False
        self._finished_emitted = False
        self._stderr_tail = ""

        self.process = QProcess(self)
        self.process.setProgram(ffmpeg_path)
        self.process.setArguments(arguments)
        self.process.setProcessChannelMode(QProcess.SeparateChannels)
        self.process.started.connect(self._on_started)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.errorOccurred.connect(self._on_process_error)
        self.process.finished.connect(self._on_finished)

    def start(self) -> None:
        self.statusChanged.emit("Starting X11 screen recording...")
        self.process.start()

    def stop(self) -> None:
        if self.process.state() == QProcess.NotRunning:
            return
        if self._stop_requested:
            return

        self._stop_requested = True
        self.statusChanged.emit("Stopping X11 recording...")
        if self.process.state() == QProcess.Starting:
            return
        self._send_stop()

    def _send_stop(self) -> None:
        if self.process.state() == QProcess.NotRunning:
            return
        self.process.write(b"q\n")
        self.process.waitForBytesWritten(100)
        self.process.closeWriteChannel()
        # Give FFmpeg plenty of time to flush the MP4 trailer cleanly.
        # Enterprise/VNC workstations and slow output filesystems can need
        # more than a few seconds after receiving the interactive 'q'.
        QTimer.singleShot(60000, self._terminate_if_running)
        QTimer.singleShot(90000, self._kill_if_running)

    def _terminate_if_running(self) -> None:
        if self.process.state() != QProcess.NotRunning:
            self.process.terminate()

    def _kill_if_running(self) -> None:
        if self.process.state() != QProcess.NotRunning:
            self.process.kill()

    def _on_started(self) -> None:
        self.statusChanged.emit("Recording (X11)...")
        self.started.emit()
        if self._stop_requested:
            self._send_stop()

    def _read_stderr(self) -> None:
        payload = bytes(self.process.readAllStandardError()).decode(
            "utf-8",
            errors="replace",
        )
        self._stderr_tail = (self._stderr_tail + payload)[-12000:]

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.FailedToStart:
            self._cleanup_partial()
            self._emit_finished_once(False, "FFmpeg could not be started.")

    def _on_finished(
        self,
        exit_code: int,
        exit_status: QProcess.ExitStatus,
    ) -> None:
        self._read_stderr()

        if (
            exit_status == QProcess.NormalExit
            and exit_code == 0
            and self._partial_path.is_file()
        ):
            try:
                self._partial_path.replace(self._final_path)
            except OSError as exc:
                self._cleanup_partial()
                self._emit_finished_once(
                    False,
                    f"Recording finished but final file could not be replaced: {exc}",
                )
                return

            self._emit_finished_once(True, "Recording saved.")
            return

        self._cleanup_partial()
        details = self._stderr_tail.strip()
        message = (
            f"X11 screen recording failed.\n\n{details[-3000:]}"
            if details
            else f"X11 screen recording failed with exit code {exit_code}."
        )
        self._emit_finished_once(False, message)

    def _cleanup_partial(self) -> None:
        try:
            if self._partial_path.exists():
                self._partial_path.unlink()
        except OSError:
            pass

    def _emit_finished_once(self, success: bool, message: str) -> None:
        if self._finished_emitted:
            return
        self._finished_emitted = True
        self.finished.emit(success, message)


class GnomeWaylandRecordingJob(QObject):
    started = Signal()
    statusChanged = Signal(str)
    finished = Signal(bool, str)

    def __init__(
        self,
        gdbus_path: str,
        ffmpeg_path: str,
        region: Tuple[int, int, int, int],
        fps: int,
        final_path: Path,
        target_size: Optional[Tuple[int, int]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._gdbus_path = str(gdbus_path)
        self._ffmpeg_path = str(ffmpeg_path)
        self._final_path = Path(final_path)
        token = uuid4().hex[:8]
        self._webm_path = self._final_path.with_name(
            f".{self._final_path.stem}.gnome-{token}.webm"
        )
        self._partial_final = self._final_path.with_name(
            f".{self._final_path.stem}.partial-{token}"
            f"{self._final_path.suffix}"
        )
        self._region = region
        self._fps = int(fps)
        self._target_size = target_size
        self._recording = False
        self._stop_requested = False
        self._stop_in_flight = False
        self._stop_attempts = 0
        self._finished_emitted = False
        self._stderr_tail = ""

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.SeparateChannels)

    def start(self) -> None:
        self.statusChanged.emit("Starting GNOME Wayland screencast...")
        self._process = QProcess(self)
        self._process.setProgram(self._gdbus_path)
        self._process.setArguments(
            gnome_screencast_start_arguments(
                self._region,
                self._webm_path,
                self._fps,
            )
        )
        self._process.setProcessChannelMode(QProcess.SeparateChannels)
        self._process.errorOccurred.connect(self._on_start_error)
        self._process.finished.connect(self._on_start_finished)
        self._process.start()

    def _on_start_error(self, error: QProcess.ProcessError) -> None:
        if error != QProcess.FailedToStart:
            return
        self._cleanup_files()
        self._emit_finished_once(
            False,
            "gdbus could not be started for GNOME Wayland capture.",
        )

    def stop(self) -> None:
        self._stop_requested = True
        if not self._recording or self._stop_in_flight:
            return
        self._request_gnome_stop()

    def _request_gnome_stop(self) -> None:
        self._stop_in_flight = True
        self._stop_attempts += 1
        self.statusChanged.emit("Stopping GNOME Wayland screencast...")
        process = QProcess(self)
        process.setProgram(self._gdbus_path)
        process.setArguments(gnome_screencast_stop_arguments())
        process.setProcessChannelMode(QProcess.SeparateChannels)
        process.errorOccurred.connect(
            lambda error, p=process: self._on_stop_error(p, error)
        )
        process.finished.connect(
            lambda exit_code, exit_status, p=process: self._on_stop_finished(
                p,
                exit_code,
                exit_status,
            )
        )
        process.start()

    def _on_stop_error(
        self,
        process: QProcess,
        error: QProcess.ProcessError,
    ) -> None:
        if error != QProcess.FailedToStart:
            return
        self._stop_in_flight = False
        if self._stop_attempts < 2:
            self.statusChanged.emit(
                "GNOME stop process could not start; retrying..."
            )
            QTimer.singleShot(500, self._request_gnome_stop)
            return
        self._emit_finished_once(
            False,
            "gdbus could not be started to stop the GNOME screencast."
            f"\n\nTemporary recording path: {self._webm_path}",
        )

    def _on_start_finished(
        self,
        exit_code: int,
        exit_status: QProcess.ExitStatus,
    ) -> None:
        stdout = bytes(self._process.readAllStandardOutput()).decode(
            "utf-8",
            errors="replace",
        )
        stderr = bytes(self._process.readAllStandardError()).decode(
            "utf-8",
            errors="replace",
        )

        success, filename = parse_gdbus_start_result(stdout)
        if (
            exit_status != QProcess.NormalExit
            or exit_code != 0
            or not success
        ):
            self._cleanup_files()
            details = stderr.strip() or stdout.strip()
            self._emit_finished_once(
                False,
                "GNOME Wayland screencast could not start."
                + (f"\n\n{details[-3000:]}" if details else ""),
            )
            return

        if filename:
            self._webm_path = Path(filename)

        self._recording = True
        self.statusChanged.emit("Recording (Wayland / GNOME)...")
        self.started.emit()
        if self._stop_requested:
            self._request_gnome_stop()

    def _on_stop_finished(
        self,
        process: QProcess,
        exit_code: int,
        exit_status: QProcess.ExitStatus,
    ) -> None:
        stdout = bytes(process.readAllStandardOutput()).decode(
            "utf-8",
            errors="replace",
        )
        stderr = bytes(process.readAllStandardError()).decode(
            "utf-8",
            errors="replace",
        )
        self._recording = False
        self._stop_in_flight = False

        if (
            exit_status != QProcess.NormalExit
            or exit_code != 0
            or not parse_gdbus_bool_result(stdout)
        ):
            details = stderr.strip() or stdout.strip()
            if self._stop_attempts < 2:
                self.statusChanged.emit(
                    "GNOME stop did not confirm; retrying..."
                )
                QTimer.singleShot(500, self._request_gnome_stop)
                return

            self._emit_finished_once(
                False,
                "GNOME Wayland screencast could not be stopped cleanly."
                + (f"\n\n{details[-3000:]}" if details else "")
                + f"\n\nTemporary recording path: {self._webm_path}",
            )
            return

        if not self._webm_path.is_file():
            self._emit_finished_once(
                False,
                f"GNOME screencast output was not found: {self._webm_path}",
            )
            return

        if self._final_path.suffix.lower() == ".webm":
            try:
                self._webm_path.replace(self._final_path)
            except OSError as exc:
                self._emit_finished_once(
                    False,
                    f"Could not finalize Wayland recording: {exc}",
                )
                return
            self._emit_finished_once(True, "Recording saved.")
            return

        self._start_transcode()

    def _start_transcode(self) -> None:
        self.statusChanged.emit("Converting Wayland screencast to final video...")
        process = QProcess(self)
        process.setProgram(self._ffmpeg_path)
        process.setArguments(
            build_wayland_transcode_arguments(
                self._webm_path,
                self._partial_final,
                self._target_size,
            )
        )
        process.setProcessChannelMode(QProcess.SeparateChannels)
        process.errorOccurred.connect(
            lambda error, p=process: self._on_transcode_error(p, error)
        )
        process.readyReadStandardError.connect(
            lambda p=process: self._read_transcode_stderr(p)
        )
        process.finished.connect(
            lambda exit_code, exit_status, p=process: self._on_transcode_finished(
                p,
                exit_code,
                exit_status,
            )
        )
        process.start()

    def _on_transcode_error(
        self,
        process: QProcess,
        error: QProcess.ProcessError,
    ) -> None:
        if error != QProcess.FailedToStart:
            return
        self._cleanup_files()
        self._emit_finished_once(
            False,
            "FFmpeg could not be started to convert the Wayland recording.",
        )

    def _read_transcode_stderr(self, process: QProcess) -> None:
        payload = bytes(process.readAllStandardError()).decode(
            "utf-8",
            errors="replace",
        )
        self._stderr_tail = (self._stderr_tail + payload)[-12000:]

    def _on_transcode_finished(
        self,
        process: QProcess,
        exit_code: int,
        exit_status: QProcess.ExitStatus,
    ) -> None:
        self._read_transcode_stderr(process)

        if (
            exit_status == QProcess.NormalExit
            and exit_code == 0
            and self._partial_final.is_file()
        ):
            try:
                self._partial_final.replace(self._final_path)
            except OSError as exc:
                self._cleanup_files()
                self._emit_finished_once(
                    False,
                    f"Converted recording could not replace final file: {exc}",
                )
                return

            self._cleanup_webm()
            self._emit_finished_once(True, "Recording saved.")
            return

        details = self._stderr_tail.strip()
        self._cleanup_files()
        self._emit_finished_once(
            False,
            "Wayland screencast conversion failed."
            + (f"\n\n{details[-3000:]}" if details else ""),
        )

    def _cleanup_webm(self) -> None:
        try:
            if self._webm_path.exists():
                self._webm_path.unlink()
        except OSError:
            pass

    def _cleanup_files(self) -> None:
        for path in (self._webm_path, self._partial_final):
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass

    def _emit_finished_once(self, success: bool, message: str) -> None:
        if self._finished_emitted:
            return
        self._finished_emitted = True
        self.finished.emit(success, message)
