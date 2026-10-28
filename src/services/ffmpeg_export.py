import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from src.utils.app_paths import application_base_dir


CropRect = Tuple[int, int, int, int]


def find_ffmpeg() -> Optional[str]:
    bundled = application_base_dir() / "tools" / "ffmpeg" / "ffmpeg.exe"
    if bundled.is_file():
        return str(bundled)

    return shutil.which("ffmpeg")


def build_export_arguments(
    input_path: Path,
    output_path: Path,
    start_ms: int,
    end_ms: int,
    crop: CropRect,
) -> List[str]:
    if end_ms <= start_ms:
        raise ValueError("End time must be after start time.")

    x, y, width, height = crop
    if min(x, y) < 0 or width <= 0 or height <= 0:
        raise ValueError("Invalid crop rectangle.")

    duration_ms = end_ms - start_ms
    return [
        "-hide_banner",
        "-nostdin",
        "-y",
        "-ss",
        f"{start_ms / 1000.0:.6f}",
        "-i",
        str(input_path),
        "-t",
        f"{duration_ms / 1000.0:.6f}",
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        f"crop={width}:{height}:{x}:{y}",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        "-progress",
        "pipe:1",
        "-nostats",
        str(output_path),
    ]


class FfmpegExportJob(QObject):
    progressChanged = Signal(int)
    statusChanged = Signal(str)
    finished = Signal(bool, str)

    def __init__(
        self,
        ffmpeg_path: str,
        arguments: List[str],
        expected_duration_ms: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._expected_duration_ms = max(1, int(expected_duration_ms))
        self._cancel_requested = False
        self._stderr_tail = ""
        self._finished_emitted = False

        self.process = QProcess(self)
        self.process.setProgram(ffmpeg_path)
        self.process.setArguments(arguments)
        self.process.setProcessChannelMode(QProcess.SeparateChannels)

        self.process.started.connect(self._on_started)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.errorOccurred.connect(self._on_process_error)
        self.process.finished.connect(self._on_finished)

    def start(self) -> None:
        self.progressChanged.emit(0)
        self.statusChanged.emit("Starting FFmpeg export...")
        self.process.start()

    def cancel(self) -> None:
        if self.process.state() == QProcess.NotRunning:
            return

        self._cancel_requested = True
        self.statusChanged.emit("Cancelling export...")
        self.process.terminate()
        QTimer.singleShot(1500, self._kill_if_running)

    def _kill_if_running(self) -> None:
        if self.process.state() != QProcess.NotRunning:
            self.process.kill()

    def _on_started(self) -> None:
        self.statusChanged.emit("Exporting video...")

    def _read_stdout(self) -> None:
        payload = bytes(self.process.readAllStandardOutput()).decode(
            "utf-8",
            errors="replace",
        )
        for line in payload.splitlines():
            key, separator, value = line.partition("=")
            if not separator:
                continue

            if key in ("out_time_us", "out_time_ms"):
                try:
                    elapsed_us = int(value)
                except ValueError:
                    continue
                elapsed_ms = elapsed_us // 1000
                self._emit_progress(elapsed_ms)
            elif key == "out_time":
                elapsed_ms = self._parse_ffmpeg_time(value)
                if elapsed_ms is not None:
                    self._emit_progress(elapsed_ms)
            elif key == "progress" and value == "end":
                self.progressChanged.emit(100)

    def _read_stderr(self) -> None:
        payload = bytes(self.process.readAllStandardError()).decode(
            "utf-8",
            errors="replace",
        )
        self._stderr_tail = (self._stderr_tail + payload)[-8000:]

    def _emit_progress(self, elapsed_ms: int) -> None:
        percent = round(100 * max(0, elapsed_ms) / self._expected_duration_ms)
        self.progressChanged.emit(min(99, max(0, percent)))

    @staticmethod
    def _parse_ffmpeg_time(value: str) -> Optional[int]:
        try:
            hours_text, minutes_text, seconds_text = value.split(":")
            total_seconds = (
                int(hours_text) * 3600
                + int(minutes_text) * 60
                + float(seconds_text)
            )
        except (ValueError, TypeError):
            return None
        return round(total_seconds * 1000)

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.FailedToStart:
            self._emit_finished_once(
                False,
                "FFmpeg could not be started.",
            )

    def _on_finished(
        self,
        exit_code: int,
        exit_status: QProcess.ExitStatus,
    ) -> None:
        self._read_stdout()
        self._read_stderr()

        if self._cancel_requested:
            self._emit_finished_once(False, "Export cancelled.")
            return

        if exit_status == QProcess.NormalExit and exit_code == 0:
            self.progressChanged.emit(100)
            self._emit_finished_once(True, "Export completed.")
            return

        details = self._stderr_tail.strip()
        if details:
            details = details[-2500:]
            message = f"FFmpeg export failed.\n\n{details}"
        else:
            message = f"FFmpeg export failed with exit code {exit_code}."
        self._emit_finished_once(False, message)

    def _emit_finished_once(self, success: bool, message: str) -> None:
        if self._finished_emitted:
            return
        self._finished_emitted = True
        self.finished.emit(success, message)
