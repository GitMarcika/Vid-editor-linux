from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from PySide6.QtCore import QSize, QUrl, Qt, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.gui.widgets.crop_video_view import CropVideoView
from src.gui.widgets.path_picker import DirectoryPicker
from src.services.ffmpeg_export import (
    FfmpegExportJob,
    build_export_arguments,
    find_ffmpeg,
)
from src.services.media_info import probe_video_info
from src.settings import AppSettings
from src.utils.timecode import format_timecode, parse_timecode


VIDEO_FILTER = (
    "Video files (*.mp4 *.mov *.mkv *.avi *.m4v *.webm *.wmv);;"
    "All files (*.*)"
)


class RawCutterTab(QWidget):
    projectChanged = Signal()

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._duration_ms = 0
        self._slider_is_being_dragged = False
        self._initialize_trim_on_duration = False
        self._current_video_path: Optional[Path] = None
        self._pending_trim: Optional[Dict[str, int]] = None
        self._pending_crop: Optional[Dict[str, int]] = None
        self._restoring_project = False
        self._crop_valid = False
        self._export_job: Optional[FfmpegExportJob] = None

        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.8)

        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)

        root = QVBoxLayout(self)

        self.input_picker = DirectoryPicker(
            "Input folder",
            settings.input_dir(),
            settings.set_input_dir,
        )
        root.addWidget(self.input_picker)

        open_row = QHBoxLayout()
        self.open_video_button = QPushButton("Open video...")
        self.file_label = QLabel("No video loaded")
        self.file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        open_row.addWidget(self.open_video_button)
        open_row.addWidget(self.file_label, 1)
        root.addLayout(open_row)

        self.video_surface = CropVideoView()
        self.player.setVideoOutput(self.video_surface.video_widget)
        root.addWidget(self.video_surface, 1)

        transport = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.setEnabled(False)

        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setRange(0, 0)
        self.timeline.setEnabled(False)

        self.time_label = QLabel("00:00.000 / 00:00.000")
        self.time_label.setMinimumWidth(175)

        transport.addWidget(self.play_button)
        transport.addWidget(self.timeline, 1)
        transport.addWidget(self.time_label)
        root.addLayout(transport)

        edit_group = QGroupBox("Trim and crop")
        form = QFormLayout(edit_group)

        trim_row = QWidget()
        trim_layout = QHBoxLayout(trim_row)
        trim_layout.setContentsMargins(0, 0, 0, 0)

        self.start_edit = QLineEdit("00:00.000")
        self.start_edit.setPlaceholderText("MM:SS.mmm")
        self.start_button = QPushButton("Set start from playhead")
        self.start_button.setEnabled(False)

        self.end_edit = QLineEdit("00:00.000")
        self.end_edit.setPlaceholderText("MM:SS.mmm")
        self.end_button = QPushButton("Set end from playhead")
        self.end_button.setEnabled(False)

        trim_layout.addWidget(QLabel("Start"))
        trim_layout.addWidget(self.start_edit)
        trim_layout.addWidget(self.start_button)
        trim_layout.addSpacing(12)
        trim_layout.addWidget(QLabel("End"))
        trim_layout.addWidget(self.end_edit)
        trim_layout.addWidget(self.end_button)
        form.addRow(trim_row)

        crop_row = QWidget()
        crop_layout = QHBoxLayout(crop_row)
        crop_layout.setContentsMargins(0, 0, 0, 0)

        self.crop_width = QSpinBox()
        self.crop_width.setRange(1, 16384)
        self.crop_width.setValue(1920)
        self.crop_width.setSuffix(" px")

        self.crop_height = QSpinBox()
        self.crop_height.setRange(1, 16384)
        self.crop_height.setValue(1080)
        self.crop_height.setSuffix(" px")

        crop_layout.addWidget(QLabel("Width"))
        crop_layout.addWidget(self.crop_width)
        crop_layout.addWidget(QLabel("Height"))
        crop_layout.addWidget(self.crop_height)
        crop_layout.addStretch(1)
        form.addRow("Crop size", crop_row)

        crop_info_row = QWidget()
        crop_info_layout = QHBoxLayout(crop_info_row)
        crop_info_layout.setContentsMargins(0, 0, 0, 0)

        self.source_size_label = QLabel("Source: -")
        self.crop_coords_label = QLabel("Crop position: x -, y -")
        crop_info_layout.addWidget(self.source_size_label)
        crop_info_layout.addSpacing(20)
        crop_info_layout.addWidget(self.crop_coords_label)
        crop_info_layout.addStretch(1)
        form.addRow("Geometry", crop_info_row)

        self.crop_help_label = QLabel(
            "Drag the crop rectangle directly on the video preview. "
            "The rectangle represents exact source-video pixels."
        )
        self.crop_help_label.setStyleSheet("color:#9aa0a6;")
        self.crop_help_label.setWordWrap(True)
        form.addRow("", self.crop_help_label)

        root.addWidget(edit_group)

        self.export_picker = DirectoryPicker(
            "Export folder",
            settings.export_dir(),
            settings.set_export_dir,
        )
        root.addWidget(self.export_picker)

        export_row = QHBoxLayout()
        self.filename_edit = QLineEdit("clip.mp4")
        self.export_button = QPushButton("Export clip")
        self.export_button.setEnabled(False)
        self.cancel_export_button = QPushButton("Cancel")
        self.cancel_export_button.setEnabled(False)

        export_row.addWidget(QLabel("Filename"))
        export_row.addWidget(self.filename_edit, 1)
        export_row.addWidget(self.export_button)
        export_row.addWidget(self.cancel_export_button)
        root.addLayout(export_row)

        self.export_progress = QProgressBar()
        self.export_progress.setRange(0, 100)
        self.export_progress.setValue(0)
        self.export_progress.setTextVisible(True)
        root.addWidget(self.export_progress)

        self.status_label = QLabel("Open a video to begin.")
        self.status_label.setStyleSheet("color:#9aa0a6;")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        self.video_surface.set_crop_size(
            self.crop_width.value(),
            self.crop_height.value(),
        )
        self._connect_signals()

    def _connect_signals(self) -> None:
        self.open_video_button.clicked.connect(self._open_video)
        self.play_button.clicked.connect(self._toggle_playback)

        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.errorOccurred.connect(self._on_player_error)

        video_sink = self.video_surface.video_widget.videoSink()
        video_sink.videoSizeChanged.connect(self._on_video_size_changed)

        self.timeline.sliderPressed.connect(self._on_slider_pressed)
        self.timeline.sliderReleased.connect(self._on_slider_released)
        self.timeline.sliderMoved.connect(self._on_slider_moved)

        self.start_button.clicked.connect(self._set_start_from_playhead)
        self.end_button.clicked.connect(self._set_end_from_playhead)
        self.start_edit.editingFinished.connect(self._validate_start_time)
        self.end_edit.editingFinished.connect(self._validate_end_time)

        self.crop_width.valueChanged.connect(self._on_crop_size_changed)
        self.crop_height.valueChanged.connect(self._on_crop_size_changed)
        self.video_surface.cropChanged.connect(self._on_crop_changed)
        self.video_surface.validityChanged.connect(self._on_crop_validity_changed)

        self.export_button.clicked.connect(self._start_export)
        self.cancel_export_button.clicked.connect(self._cancel_export)

    def _open_video(self) -> None:
        start_dir = self.input_picker.path() or str(Path.home())
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open video",
            start_dir,
            VIDEO_FILTER,
        )
        if filename:
            self._load_video_path(Path(filename), mark_changed=True)

    def _load_video_path(self, path: Path, mark_changed: bool) -> None:
        path = Path(path)
        self._current_video_path = path
        self.input_picker.set_path(str(path.parent))
        self.file_label.setText(path.name)
        self.file_label.setToolTip(str(path))

        self.player.stop()
        self.timeline.setRange(0, 0)
        self.timeline.setValue(0)
        self._duration_ms = 0
        self._initialize_trim_on_duration = self._pending_trim is None
        self.start_edit.setText(format_timecode(0))
        self.end_edit.setText(format_timecode(0))
        self._set_time_edit_valid(self.start_edit, True)
        self._set_time_edit_valid(self.end_edit, True)

        self.video_surface.reset_for_new_video()
        self.source_size_label.setText("Source: loading...")
        self.crop_coords_label.setText("Crop position: x -, y -")
        self._crop_valid = False
        self._update_export_enabled()

        if self._pending_crop is not None:
            crop = self._pending_crop
            self.crop_width.setValue(int(crop.get("width", self.crop_width.value())))
            self.crop_height.setValue(int(crop.get("height", self.crop_height.value())))
            self.video_surface.set_crop_rect(
                int(crop.get("x", 0)),
                int(crop.get("y", 0)),
                int(crop.get("width", self.crop_width.value())),
                int(crop.get("height", self.crop_height.value())),
            )

        self._apply_ffprobe_metadata(path)

        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.play_button.setEnabled(True)
        self.timeline.setEnabled(True)
        self.start_button.setEnabled(True)
        self.end_button.setEnabled(True)
        self.status_label.setText(f"Loaded: {path.name}")

        if mark_changed and not self._restoring_project:
            self.projectChanged.emit()

    def _apply_ffprobe_metadata(self, path: Path) -> None:
        try:
            info = probe_video_info(path)
            size = QSize(info.width, info.height)
            self.video_surface.set_video_size(size)
            self.source_size_label.setText(
                f"Source: {info.width} x {info.height} px"
            )

            if self._pending_crop is not None:
                crop = self._pending_crop
                self.video_surface.set_crop_rect(
                    int(crop.get("x", 0)),
                    int(crop.get("y", 0)),
                    int(crop.get("width", self.crop_width.value())),
                    int(crop.get("height", self.crop_height.value())),
                )
                self._pending_crop = None
        except (OSError, RuntimeError, ValueError) as exc:
            self.status_label.setText(
                f"FFprobe video metadata unavailable: {exc}"
            )

            if info.duration_ms > 0:
                self._on_duration_changed(info.duration_ms)

    def _toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _on_playback_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
    ) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setText("Pause")
        else:
            self.play_button.setText("Play")

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._duration_ms = max(0, int(duration_ms))
        self.timeline.setRange(0, self._duration_ms)

        if self._pending_trim is not None and self._duration_ms > 0:
            start_ms = max(0, min(
                int(self._pending_trim.get("start_ms", 0)),
                self._duration_ms,
            ))
            end_ms = max(start_ms, min(
                int(self._pending_trim.get("end_ms", self._duration_ms)),
                self._duration_ms,
            ))
            self.start_edit.setText(format_timecode(start_ms))
            self.end_edit.setText(format_timecode(end_ms))
            self._pending_trim = None
            self._initialize_trim_on_duration = False
        elif self._initialize_trim_on_duration and self._duration_ms > 0:
            self.start_edit.setText(format_timecode(0))
            self.end_edit.setText(format_timecode(self._duration_ms))
            self._initialize_trim_on_duration = False

        self._update_time_label()
        self._update_export_enabled()

    def _on_position_changed(self, position_ms: int) -> None:
        if not self._slider_is_being_dragged:
            self.timeline.setValue(max(0, int(position_ms)))
            self._update_time_label(position_ms)

    def _on_slider_pressed(self) -> None:
        self._slider_is_being_dragged = True

    def _on_slider_moved(self, value: int) -> None:
        self._update_time_label(value)

    def _on_slider_released(self) -> None:
        self._slider_is_being_dragged = False
        position = self.timeline.value()
        self.player.setPosition(position)
        self._update_time_label(position)

    def _update_time_label(self, position_ms: Optional[int] = None) -> None:
        if position_ms is None:
            position_ms = self.timeline.value()
        self.time_label.setText(
            f"{format_timecode(position_ms)} / {format_timecode(self._duration_ms)}"
        )

    def _set_start_from_playhead(self) -> None:
        current = self.player.position()
        end_ms = self._time_from_edit(self.end_edit)

        if end_ms is not None and current > end_ms:
            self._show_validation_error(
                self.start_edit,
                "Start time cannot be after end time.",
            )
            return

        self.start_edit.setText(format_timecode(current))
        self._set_time_edit_valid(self.start_edit, True)
        self.status_label.setText("Start time set from current playhead.")
        self._mark_project_changed()
        self._update_export_enabled()

    def _set_end_from_playhead(self) -> None:
        current = self.player.position()
        start_ms = self._time_from_edit(self.start_edit)

        if start_ms is not None and current < start_ms:
            self._show_validation_error(
                self.end_edit,
                "End time cannot be before start time.",
            )
            return

        self.end_edit.setText(format_timecode(current))
        self._set_time_edit_valid(self.end_edit, True)
        self.status_label.setText("End time set from current playhead.")
        self._mark_project_changed()
        self._update_export_enabled()

    def _validate_start_time(self) -> None:
        value = self._validated_time_value(self.start_edit)
        if value is None:
            self._update_export_enabled()
            return

        end_ms = self._time_from_edit(self.end_edit)
        if end_ms is not None and value > end_ms:
            self._show_validation_error(
                self.start_edit,
                "Start time cannot be after end time.",
            )
            self._update_export_enabled()
            return

        self.start_edit.setText(format_timecode(value))
        self._set_time_edit_valid(self.start_edit, True)
        self.status_label.setText("Start time updated.")
        self._mark_project_changed()
        self._update_export_enabled()

    def _validate_end_time(self) -> None:
        value = self._validated_time_value(self.end_edit)
        if value is None:
            self._update_export_enabled()
            return

        start_ms = self._time_from_edit(self.start_edit)
        if start_ms is not None and value < start_ms:
            self._show_validation_error(
                self.end_edit,
                "End time cannot be before start time.",
            )
            self._update_export_enabled()
            return

        self.end_edit.setText(format_timecode(value))
        self._set_time_edit_valid(self.end_edit, True)
        self.status_label.setText("End time updated.")
        self._mark_project_changed()
        self._update_export_enabled()

    def _validated_time_value(self, edit: QLineEdit) -> Optional[int]:
        value = self._time_from_edit(edit)
        if value is None:
            self._show_validation_error(
                edit,
                "Invalid time. Use MM:SS.mmm or HH:MM:SS.mmm.",
            )
            return None

        if self._duration_ms > 0 and value > self._duration_ms:
            self._show_validation_error(
                edit,
                "Time cannot be beyond the end of the video.",
            )
            return None

        return value

    @staticmethod
    def _time_from_edit(edit: QLineEdit) -> Optional[int]:
        try:
            return parse_timecode(edit.text())
        except ValueError:
            return None

    def _show_validation_error(self, edit: QLineEdit, message: str) -> None:
        self._set_time_edit_valid(edit, False)
        self.status_label.setText(message)

    @staticmethod
    def _set_time_edit_valid(edit: QLineEdit, valid: bool) -> None:
        if valid:
            edit.setStyleSheet("")
        else:
            edit.setStyleSheet("border:1px solid #d93025;")

    def _on_video_size_changed(self) -> None:
        size = self.video_surface.video_widget.videoSink().videoSize()
        self.video_surface.set_video_size(size)

        if self._pending_crop is not None and size.isValid():
            crop = self._pending_crop
            self.video_surface.set_crop_rect(
                int(crop.get("x", 0)),
                int(crop.get("y", 0)),
                int(crop.get("width", self.crop_width.value())),
                int(crop.get("height", self.crop_height.value())),
            )
            self._pending_crop = None

        if size.isValid():
            self.source_size_label.setText(
                f"Source: {size.width()} x {size.height()} px"
            )
        else:
            self.source_size_label.setText("Source: -")

        self._update_export_enabled()

    def _on_crop_size_changed(self) -> None:
        self.video_surface.set_crop_size(
            self.crop_width.value(),
            self.crop_height.value(),
        )
        self._mark_project_changed()

    def _on_crop_changed(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        self.crop_coords_label.setText(
            f"Crop position: x {x}, y {y} | {width} x {height} px"
        )
        self._mark_project_changed()

    def _on_crop_validity_changed(self, valid: bool, message: str) -> None:
        self._crop_valid = valid
        if valid:
            self.crop_coords_label.setStyleSheet("")
            x, y, width, height = self.video_surface.crop_rect_source()
            self.status_label.setText(
                f"Crop ready: x={x}, y={y}, {width}x{height}px."
            )
        else:
            self.crop_coords_label.setStyleSheet("color:#e57373;")
            if message:
                self.status_label.setText(message)
        self._update_export_enabled()

    def _update_export_enabled(self) -> None:
        start_ms = self._time_from_edit(self.start_edit)
        end_ms = self._time_from_edit(self.end_edit)
        times_valid = (
            start_ms is not None
            and end_ms is not None
            and end_ms > start_ms
            and (self._duration_ms <= 0 or end_ms <= self._duration_ms)
        )
        ready = (
            self._current_video_path is not None
            and self._current_video_path.is_file()
            and self._crop_valid
            and times_valid
            and self._export_job is None
        )
        self.export_button.setEnabled(ready)

    def _start_export(self) -> None:
        if self._current_video_path is None or not self._current_video_path.is_file():
            QMessageBox.warning(self, "Export", "The source video is missing.")
            return

        if not self.video_surface.is_crop_valid():
            QMessageBox.warning(self, "Export", "The crop rectangle is not valid.")
            return

        start_ms = self._validated_time_value(self.start_edit)
        end_ms = self._validated_time_value(self.end_edit)
        if start_ms is None or end_ms is None or end_ms <= start_ms:
            QMessageBox.warning(
                self,
                "Export",
                "The trim start/end values are not valid.",
            )
            return

        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            QMessageBox.critical(
                self,
                "FFmpeg not found",
                "FFmpeg was not found. Run ./setup_ffmpeg.sh or place the "
                "Linux ffmpeg binary in tools/ffmpeg/ffmpeg.",
            )
            return

        filename = self.filename_edit.text().strip()
        if not filename:
            QMessageBox.warning(self, "Export", "Enter an output filename.")
            return

        output_dir = Path(self.export_picker.path())
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Export",
                f"Could not create the export folder:\n{exc}",
            )
            return

        output_path = output_dir / filename
        if output_path.suffix == "":
            output_path = output_path.with_suffix(".mp4")
            self.filename_edit.setText(output_path.name)

        if output_path.exists():
            answer = QMessageBox.question(
                self,
                "Overwrite file?",
                f"{output_path.name} already exists. Overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        crop = self.video_surface.crop_rect_source()
        partial_path = output_path.with_name(
            f".{output_path.stem}.partial-{uuid4().hex[:8]}"
            f"{output_path.suffix}"
        )

        try:
            arguments = build_export_arguments(
                self._current_video_path,
                partial_path,
                start_ms,
                end_ms,
                crop,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Export", str(exc))
            return

        self.export_progress.setValue(0)
        self.export_button.setEnabled(False)
        self.cancel_export_button.setEnabled(True)

        self._export_job = FfmpegExportJob(
            ffmpeg_path,
            arguments,
            end_ms - start_ms,
            parent=self,
        )
        self._export_job.progressChanged.connect(self.export_progress.setValue)
        self._export_job.statusChanged.connect(self.status_label.setText)
        self._export_job.finished.connect(
            lambda success, message: self._on_export_finished(
                success,
                message,
                output_path,
                partial_path,
            )
        )
        self._export_job.start()

    def _cancel_export(self) -> None:
        if self._export_job is not None:
            self._export_job.cancel()

    def _on_export_finished(
        self,
        success: bool,
        message: str,
        output_path: Path,
        partial_path: Path,
    ) -> None:
        self._export_job = None
        self.cancel_export_button.setEnabled(False)
        self._update_export_enabled()

        if success:
            try:
                partial_path.replace(output_path)
            except OSError as exc:
                try:
                    if partial_path.exists():
                        partial_path.unlink()
                except OSError:
                    pass
                self.status_label.setText("Could not finalize export.")
                QMessageBox.critical(
                    self,
                    "Export failed",
                    f"Video rendered but could not replace the final file:\n{exc}",
                )
                return

            self.status_label.setText(f"Export completed: {output_path}")
            QMessageBox.information(
                self,
                "Export completed",
                f"Video saved to:\n{output_path}",
            )
        else:
            try:
                if partial_path.exists():
                    partial_path.unlink()
            except OSError:
                pass
            self.status_label.setText(message.splitlines()[0])
            if message != "Export cancelled.":
                QMessageBox.critical(self, "Export failed", message)

    def project_state(self) -> Dict[str, Any]:
        if self._current_video_path is None:
            return {}

        start_ms = self._time_from_edit(self.start_edit)
        end_ms = self._time_from_edit(self.end_edit)
        x, y, width, height = self.video_surface.crop_rect_source()

        return {
            "source_video": str(self._current_video_path),
            "trim_start_ms": int(start_ms or 0),
            "trim_end_ms": int(end_ms or self._duration_ms),
            "crop": {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
            },
        }

    def load_project_state(self, state: Dict[str, Any]) -> None:
        self._restoring_project = True
        try:
            self.clear_project()

            if not state:
                return

            source = state.get("source_video")
            if not source:
                return

            source_path = Path(str(source))
            if not source_path.is_file():
                raise FileNotFoundError(str(source_path))

            self._pending_trim = {
                "start_ms": int(state.get("trim_start_ms", 0)),
                "end_ms": int(state.get("trim_end_ms", 0)),
            }

            crop = state.get("crop") or {}
            self._pending_crop = {
                "x": int(crop.get("x", 0)),
                "y": int(crop.get("y", 0)),
                "width": int(crop.get("width", 1920)),
                "height": int(crop.get("height", 1080)),
            }

            self._load_video_path(source_path, mark_changed=False)
        finally:
            self._restoring_project = False

    def is_exporting(self) -> bool:
        return self._export_job is not None

    def cancel_export(self) -> None:
        self._cancel_export()

    def clear_project(self) -> None:
        if self._export_job is not None:
            self._export_job.cancel()
            self._export_job = None

        self.player.stop()
        self.player.setSource(QUrl())
        self._current_video_path = None
        self._pending_trim = None
        self._pending_crop = None
        self._duration_ms = 0
        self._initialize_trim_on_duration = False
        self._crop_valid = False

        self.video_surface.reset_for_new_video()
        self.file_label.setText("No video loaded")
        self.file_label.setToolTip("")
        self.source_size_label.setText("Source: -")
        self.crop_coords_label.setText("Crop position: x -, y -")
        self.start_edit.setText("00:00.000")
        self.end_edit.setText("00:00.000")
        self.timeline.setRange(0, 0)
        self.timeline.setValue(0)
        self.time_label.setText("00:00.000 / 00:00.000")
        self.play_button.setText("Play")
        self.play_button.setEnabled(False)
        self.timeline.setEnabled(False)
        self.start_button.setEnabled(False)
        self.end_button.setEnabled(False)
        self.cancel_export_button.setEnabled(False)
        self.export_progress.setValue(0)
        self.status_label.setText("Open a video to begin.")
        self._update_export_enabled()

    def _mark_project_changed(self) -> None:
        if not self._restoring_project:
            self.projectChanged.emit()

    def _on_player_error(
        self,
        error: QMediaPlayer.Error,
        error_string: str,
    ) -> None:
        if error == QMediaPlayer.Error.NoError:
            return
        message = error_string or self.player.errorString() or "Unknown media error"
        self.status_label.setText(
            f"Playback error: {message}. FFprobe-based crop/export may still work."
        )
