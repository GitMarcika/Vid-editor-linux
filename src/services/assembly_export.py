import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import uuid4

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from src.services.media_info import VideoInfo, probe_video_info
from src.utils.overlays import sort_text_overlays


def _escape_ass_text(value: str) -> str:
    return (
        str(value)
        .replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\r\n", r"\N")
        .replace("\n", r"\N")
        .replace("\r", r"\N")
    )


def _ass_time(milliseconds: int) -> str:
    milliseconds = max(0, int(milliseconds))
    total_cs = milliseconds // 10
    hours, remainder = divmod(total_cs, 360000)
    minutes, remainder = divmod(remainder, 6000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def _hex_to_ass_color(hex_color: str, alpha: int = 0) -> str:
    text = str(hex_color).strip().lstrip("#")
    if len(text) != 6:
        text = "ffffff"

    try:
        red = int(text[0:2], 16)
        green = int(text[2:4], 16)
        blue = int(text[4:6], 16)
    except ValueError:
        red, green, blue = 255, 255, 255

    alpha = max(0, min(255, int(alpha)))
    return f"&H{alpha:02X}{blue:02X}{green:02X}{red:02X}"


def _opacity_to_ass_alpha(opacity: int) -> int:
    opacity = max(0, min(255, int(opacity)))
    return 255 - opacity


def build_ass_subtitles(
    overlays: Iterable[Dict[str, Any]],
    width: int,
    height: int,
) -> str:
    width = max(2, int(width))
    height = max(2, int(height))
    scale = height / 720.0

    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        (
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding"
        ),
    ]
    style_lines: List[str] = []
    event_lines = [
        "",
        "[Events]",
        (
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
            "MarginV, Effect, Text"
        ),
    ]

    for index, overlay in enumerate(sort_text_overlays(overlays)):
        text = _escape_ass_text(str(overlay.get("text", "")))
        if not text:
            continue

        start = _ass_time(int(overlay.get("start_ms", 0)))
        end = _ass_time(int(overlay.get("end_ms", 0)))

        x = round(float(overlay.get("x_norm", 0.5)) * width)
        y = round(float(overlay.get("y_norm", 0.5)) * height)

        font_family = str(overlay.get("font_family", "Arial")).replace(",", " ")
        font_size = max(6.0, float(overlay.get("font_size", 28)) * scale)

        text_color = _hex_to_ass_color(
            str(overlay.get("text_color", "#ffffff")),
            0,
        )

        outline_enabled = bool(overlay.get("outline_enabled", False))
        outline_width = (
            max(0.0, float(overlay.get("outline_width", 2)) * scale)
            if outline_enabled
            else 0.0
        )
        outline_color = _hex_to_ass_color(
            str(overlay.get("outline_color", "#000000")),
            0 if outline_enabled else 255,
        )

        shadow_enabled = bool(overlay.get("shadow_enabled", False))
        shadow_width = (
            max(
                0.0,
                (
                    (
                        abs(float(overlay.get("shadow_offset_x", 3)))
                        + abs(float(overlay.get("shadow_offset_y", 3)))
                    )
                    * 0.5
                    + float(overlay.get("shadow_blur", 8)) * 0.25
                )
                * scale,
            )
            if shadow_enabled
            else 0.0
        )
        shadow_color = _hex_to_ass_color(
            str(overlay.get("shadow_color", "#000000")),
            _opacity_to_ass_alpha(
                int(overlay.get("shadow_opacity", 160))
            )
            if shadow_enabled
            else 255,
        )

        text_style = f"Text{index}"
        style_lines.append(
            "Style: "
            f"{text_style},{font_family},{font_size:.2f},"
            f"{text_color},{text_color},"
            f"{outline_color},{shadow_color},"
            "0,0,0,0,100,100,0,0,1,"
            f"{outline_width:.2f},{shadow_width:.2f},7,0,0,0,1"
        )

        if bool(overlay.get("background_enabled", False)):
            background_color = _hex_to_ass_color(
                str(overlay.get("background_color", "#000000")),
                _opacity_to_ass_alpha(
                    int(overlay.get("background_opacity", 170))
                ),
            )
            padding = max(
                0.0,
                float(overlay.get("background_padding", 8)) * scale,
            )
            bg_style = f"Bg{index}"
            transparent_text = "&HFFFFFFFF"
            style_lines.append(
                "Style: "
                f"{bg_style},{font_family},{font_size:.2f},"
                f"{transparent_text},{transparent_text},"
                f"{background_color},{background_color},"
                "0,0,0,0,100,100,0,0,3,"
                f"{padding:.2f},0,7,0,0,0,1"
            )
            event_lines.append(
                "Dialogue: "
                f"0,{start},{end},{bg_style},,0,0,0,,"
                f"{{\\pos({x},{y})}}{text}"
            )

        event_lines.append(
            "Dialogue: "
            f"1,{start},{end},{text_style},,0,0,0,,"
            f"{{\\pos({x},{y})}}{text}"
        )

    return "\n".join(header + style_lines + event_lines) + "\n"


def _escape_filter_path(path: Path) -> str:
    text = str(path.resolve()).replace("\\", "/")
    text = text.replace(":", r"\:")
    text = text.replace("'", r"\'")
    return text


def build_filter_graph(
    clip_infos: Sequence[Tuple[Path, int, VideoInfo]],
    width: int,
    height: int,
    fps: float,
    ass_path: Optional[Path],
) -> str:
    parts: List[str] = []

    for index, (_path, duration_ms, info) in enumerate(clip_infos):
        duration_sec = max(0.001, duration_ms / 1000.0)
        parts.append(
            f"[{index}:v]"
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fps={fps:.6f},"
            f"trim=duration={duration_sec:.6f},"
            f"setsar=1,setpts=PTS-STARTPTS[v{index}]"
        )

        if info.has_audio:
            parts.append(
                f"[{index}:a]"
                "aresample=48000,"
                "aformat=sample_fmts=fltp:sample_rates=48000:"
                "channel_layouts=stereo,"
                f"apad,atrim=0:{duration_sec:.6f},"
                f"asetpts=PTS-STARTPTS[a{index}]"
            )
        else:
            parts.append(
                "anullsrc=channel_layout=stereo:sample_rate=48000,"
                f"atrim=0:{duration_sec:.6f},"
                f"asetpts=PTS-STARTPTS[a{index}]"
            )

    concat_inputs = "".join(
        f"[v{index}][a{index}]"
        for index in range(len(clip_infos))
    )
    parts.append(
        f"{concat_inputs}concat=n={len(clip_infos)}:v=1:a=1[vcat][acat]"
    )

    if ass_path is not None:
        ass_filter_path = _escape_filter_path(ass_path)
        parts.append(f"[vcat]ass='{ass_filter_path}'[vout]")
    else:
        parts.append("[vcat]null[vout]")

    return ";\n".join(parts) + "\n"


def build_assembly_export_arguments(
    clips: Sequence[Dict[str, Any]],
    overlays: Sequence[Dict[str, Any]],
    output_path: Path,
    work_dir: Path,
) -> Tuple[List[str], int, int, int, float]:
    if not clips:
        raise ValueError("At least one clip is required.")

    clip_infos: List[Tuple[Path, int, VideoInfo]] = []
    for clip in clips:
        path = Path(str(clip.get("path", "")))
        if not path.is_file():
            raise FileNotFoundError(str(path))

        duration_ms = max(1, int(clip.get("duration_ms", 0)))
        info = probe_video_info(path)
        clip_infos.append((path, duration_ms, info))

    first_info = clip_infos[0][2]
    width = max(2, first_info.width - (first_info.width % 2))
    height = max(2, first_info.height - (first_info.height % 2))
    fps = max(1.0, min(120.0, float(first_info.fps)))

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    has_overlays = any(
        str(overlay.get("text", "")).strip()
        for overlay in overlays
    )
    ass_path: Optional[Path] = None
    if has_overlays:
        ass_path = work_dir / "overlays.ass"
        ass_path.write_text(
            build_ass_subtitles(overlays, width, height),
            encoding="utf-8-sig",
        )

    filter_path = work_dir / "filter_complex.txt"
    filter_path.write_text(
        build_filter_graph(
            clip_infos,
            width,
            height,
            fps,
            ass_path,
        ),
        encoding="utf-8",
    )

    args: List[str] = [
        "-hide_banner",
        "-nostdin",
        "-y",
    ]
    for path, _duration_ms, _info in clip_infos:
        args.extend(["-i", str(path)])

    args.extend(
        [
            "-filter_complex_script",
            str(filter_path),
            "-map",
            "[vout]",
            "-map",
            "[acat]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
        ]
    )

    if output_path.suffix.lower() in (".mp4", ".mov", ".m4v"):
        args.extend(["-movflags", "+faststart"])

    args.extend(
        [
            "-progress",
            "pipe:1",
            "-nostats",
            str(output_path),
        ]
    )

    total_duration_ms = sum(
        max(0, int(clip.get("duration_ms", 0)))
        for clip in clips
    )
    return args, total_duration_ms, width, height, fps


class AssemblyExportJob(QObject):
    progressChanged = Signal(int)
    statusChanged = Signal(str)
    finished = Signal(bool, str)

    def __init__(
        self,
        ffmpeg_path: str,
        clips: Sequence[Dict[str, Any]],
        overlays: Sequence[Dict[str, Any]],
        output_path: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._final_output_path = Path(output_path)
        self._output_path = self._final_output_path.with_name(
            f".{self._final_output_path.stem}.partial-"
            f"{uuid4().hex[:8]}{self._final_output_path.suffix}"
        )
        self._work_dir = Path(tempfile.mkdtemp(prefix="videditor-export-"))
        self._cancel_requested = False
        self._finished_emitted = False
        self._stderr_tail = ""

        try:
            (
                arguments,
                self._expected_duration_ms,
                self.output_width,
                self.output_height,
                self.output_fps,
            ) = build_assembly_export_arguments(
                clips,
                overlays,
                self._output_path,
                self._work_dir,
            )
        except Exception:
            shutil.rmtree(self._work_dir, ignore_errors=True)
            raise

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
        self.statusChanged.emit("Preparing assembly export...")
        self.process.start()

    def cancel(self) -> None:
        if self.process.state() == QProcess.NotRunning:
            return

        self._cancel_requested = True
        self.statusChanged.emit("Cancelling assembly export...")
        self.process.terminate()
        QTimer.singleShot(1500, self._kill_if_running)

    def _kill_if_running(self) -> None:
        if self.process.state() != QProcess.NotRunning:
            self.process.kill()

    def _on_started(self) -> None:
        self.statusChanged.emit("Rendering assembled video...")

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
                self._emit_progress(elapsed_us // 1000)
            elif key == "out_time":
                milliseconds = self._parse_ffmpeg_time(value)
                if milliseconds is not None:
                    self._emit_progress(milliseconds)
            elif key == "progress" and value == "end":
                self.progressChanged.emit(100)

    def _read_stderr(self) -> None:
        payload = bytes(self.process.readAllStandardError()).decode(
            "utf-8",
            errors="replace",
        )
        self._stderr_tail = (self._stderr_tail + payload)[-16000:]

    def _emit_progress(self, elapsed_ms: int) -> None:
        denominator = max(1, self._expected_duration_ms)
        percent = round(100 * max(0, elapsed_ms) / denominator)
        self.progressChanged.emit(min(99, max(0, percent)))

    @staticmethod
    def _parse_ffmpeg_time(value: str):
        try:
            hours_text, minutes_text, seconds_text = value.split(":")
            seconds = (
                int(hours_text) * 3600
                + int(minutes_text) * 60
                + float(seconds_text)
            )
        except (ValueError, TypeError):
            return None
        return round(seconds * 1000)

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.FailedToStart:
            self._cleanup_partial_output()
            self._cleanup_work_dir()
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
            self._cleanup_partial_output()
            self._cleanup_work_dir()
            self._emit_finished_once(False, "Assembly export cancelled.")
            return

        if (
            exit_status == QProcess.NormalExit
            and exit_code == 0
            and self._output_path.is_file()
        ):
            try:
                self._output_path.replace(self._final_output_path)
            except OSError as exc:
                self._cleanup_partial_output()
                self._cleanup_work_dir()
                self._emit_finished_once(
                    False,
                    f"Rendered video could not replace the final file: {exc}",
                )
                return

            self.progressChanged.emit(100)
            self._cleanup_work_dir()
            self._emit_finished_once(True, "Assembly export completed.")
            return

        details = self._stderr_tail.strip()
        self._cleanup_partial_output()
        self._cleanup_work_dir()

        if details:
            message = f"Assembly export failed.\n\n{details[-4000:]}"
        else:
            message = (
                "Assembly export failed "
                f"with exit code {exit_code}."
            )

        self._emit_finished_once(False, message)

    def _cleanup_partial_output(self) -> None:
        try:
            if self._output_path.exists():
                self._output_path.unlink()
        except OSError:
            pass

    def _cleanup_work_dir(self) -> None:
        shutil.rmtree(self._work_dir, ignore_errors=True)

    def _emit_finished_once(self, success: bool, message: str) -> None:
        if self._finished_emitted:
            return
        self._finished_emitted = True
        self.finished.emit(success, message)
