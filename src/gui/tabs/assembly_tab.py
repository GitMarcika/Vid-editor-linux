from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from PySide6.QtCore import QSize, QUrl, Qt, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.gui.widgets.assembly_preview import AssemblyPreview
from src.gui.widgets.color_button import ColorButton
from src.gui.widgets.path_picker import DirectoryPicker
from src.services.assembly_export import AssemblyExportJob
from src.services.ffmpeg_export import find_ffmpeg
from src.services.media_info import extract_thumbnail_png, probe_duration_ms
from src.settings import AppSettings
from src.utils.overlays import normalize_text_overlay, sort_text_overlays
from src.utils.timecode import format_timecode, parse_timecode
from src.utils.timeline import ClipSpan, build_clip_spans, locate_global_position, total_duration_ms


VIDEO_FILTER = (
    "Video files (*.mp4 *.mov *.mkv *.avi *.m4v *.webm *.wmv);;"
    "All files (*.*)"
)


class AssemblyTab(QWidget):
    projectChanged = Signal()

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._text_overlays: List[Dict[str, Any]] = []
        self._spans: List[ClipSpan] = []
        self._slider_is_being_dragged = False
        self._was_playing_before_seek = False
        self._continuous_playback = False
        self._current_clip_id: Optional[str] = None
        self._pending_seek_ms: Optional[int] = None
        self._pending_autoplay = False
        self._restoring_project = False
        self._assembly_export_job: Optional[AssemblyExportJob] = None
        self._assembly_export_output: Optional[Path] = None

        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.8)

        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)

        root = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.toggle_clips_button = QPushButton("Hide clips")
        self.toggle_clips_button.setCheckable(True)
        self.toggle_clips_button.setChecked(True)

        self.toggle_texts_button = QPushButton("Hide text panel")
        self.toggle_texts_button.setCheckable(True)
        self.toggle_texts_button.setChecked(True)

        toolbar.addWidget(self.toggle_clips_button)
        toolbar.addWidget(self.toggle_texts_button)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.splitter = QSplitter(Qt.Horizontal)

        self.clip_panel = QWidget()
        left_layout = QVBoxLayout(self.clip_panel)
        left_layout.addWidget(QLabel("Clips"))

        self.clip_list = QListWidget()
        self.clip_list.setDragDropMode(QListWidget.InternalMove)
        self.clip_list.setDefaultDropAction(Qt.MoveAction)
        self.clip_list.setIconSize(QSize(160, 90))
        self.clip_list.setSpacing(4)
        left_layout.addWidget(self.clip_list, 1)

        clip_buttons = QHBoxLayout()
        self.add_clip_button = QPushButton("Add")
        self.remove_clip_button = QPushButton("Remove")
        clip_buttons.addWidget(self.add_clip_button)
        clip_buttons.addWidget(self.remove_clip_button)
        left_layout.addLayout(clip_buttons)

        center = QWidget()
        center_layout = QVBoxLayout(center)

        self.preview = AssemblyPreview()
        self.player.setVideoOutput(self.preview.video_item)
        center_layout.addWidget(self.preview, 1)

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
        center_layout.addLayout(transport)

        self.text_panel = QGroupBox("Text overlays")
        right_layout = QVBoxLayout(self.text_panel)

        self.text_list = QListWidget()
        right_layout.addWidget(self.text_list, 1)

        text_buttons = QHBoxLayout()
        self.add_text_button = QPushButton("Add text")
        self.remove_text_button = QPushButton("Remove")
        self.add_text_button.setEnabled(False)
        self.remove_text_button.setEnabled(False)
        text_buttons.addWidget(self.add_text_button)
        text_buttons.addWidget(self.remove_text_button)
        right_layout.addLayout(text_buttons)

        editor_group = QGroupBox("Selected text")
        editor_form = QFormLayout(editor_group)

        self.text_editor = QPlainTextEdit()
        self.text_editor.setPlaceholderText("Select a text overlay")
        self.text_editor.setMaximumHeight(90)
        self.text_editor.setEnabled(False)
        editor_form.addRow("Text", self.text_editor)

        start_row = QWidget()
        start_layout = QHBoxLayout(start_row)
        start_layout.setContentsMargins(0, 0, 0, 0)
        self.text_start_edit = QLineEdit("00:00.000")
        self.text_start_edit.setEnabled(False)
        self.set_text_start_button = QPushButton("Set from playhead")
        self.set_text_start_button.setEnabled(False)
        start_layout.addWidget(self.text_start_edit)
        start_layout.addWidget(self.set_text_start_button)
        editor_form.addRow("Start", start_row)

        end_row = QWidget()
        end_layout = QHBoxLayout(end_row)
        end_layout.setContentsMargins(0, 0, 0, 0)
        self.text_end_edit = QLineEdit("00:00.000")
        self.text_end_edit.setEnabled(False)
        self.set_text_end_button = QPushButton("Set from playhead")
        self.set_text_end_button.setEnabled(False)
        end_layout.addWidget(self.text_end_edit)
        end_layout.addWidget(self.set_text_end_button)
        editor_form.addRow("End", end_row)

        self.text_position_label = QLabel("Position: -")
        editor_form.addRow("Position", self.text_position_label)

        style_group = QGroupBox("Style")
        style_form = QFormLayout(style_group)

        self.font_combo = QFontComboBox()
        self.font_combo.setEnabled(False)
        style_form.addRow("Font", self.font_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 300)
        self.font_size_spin.setValue(28)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setEnabled(False)
        style_form.addRow("Size", self.font_size_spin)

        self.text_color_button = ColorButton("#ffffff")
        self.text_color_button.setEnabled(False)
        style_form.addRow("Text color", self.text_color_button)

        self.background_enabled_check = QCheckBox("Fitted background box")
        self.background_enabled_check.setEnabled(False)
        style_form.addRow("Background", self.background_enabled_check)

        self.background_color_button = ColorButton("#000000")
        self.background_color_button.setEnabled(False)
        style_form.addRow("Background color", self.background_color_button)

        self.background_opacity_spin = QSpinBox()
        self.background_opacity_spin.setRange(0, 100)
        self.background_opacity_spin.setValue(67)
        self.background_opacity_spin.setSuffix(" %")
        self.background_opacity_spin.setEnabled(False)
        style_form.addRow("Background opacity", self.background_opacity_spin)

        self.background_padding_spin = QSpinBox()
        self.background_padding_spin.setRange(0, 100)
        self.background_padding_spin.setValue(8)
        self.background_padding_spin.setSuffix(" px")
        self.background_padding_spin.setEnabled(False)
        style_form.addRow("Padding", self.background_padding_spin)

        self.outline_enabled_check = QCheckBox("Enable outline")
        self.outline_enabled_check.setEnabled(False)
        style_form.addRow("Outline", self.outline_enabled_check)

        self.outline_color_button = ColorButton("#000000")
        self.outline_color_button.setEnabled(False)
        style_form.addRow("Outline color", self.outline_color_button)

        self.outline_width_spin = QSpinBox()
        self.outline_width_spin.setRange(0, 20)
        self.outline_width_spin.setValue(2)
        self.outline_width_spin.setSuffix(" px")
        self.outline_width_spin.setEnabled(False)
        style_form.addRow("Outline width", self.outline_width_spin)

        self.shadow_enabled_check = QCheckBox("Enable shadow")
        self.shadow_enabled_check.setEnabled(False)
        style_form.addRow("Shadow", self.shadow_enabled_check)

        self.shadow_color_button = ColorButton("#000000")
        self.shadow_color_button.setEnabled(False)
        style_form.addRow("Shadow color", self.shadow_color_button)

        self.shadow_opacity_spin = QSpinBox()
        self.shadow_opacity_spin.setRange(0, 100)
        self.shadow_opacity_spin.setValue(63)
        self.shadow_opacity_spin.setSuffix(" %")
        self.shadow_opacity_spin.setEnabled(False)
        style_form.addRow("Shadow opacity", self.shadow_opacity_spin)

        self.shadow_blur_spin = QSpinBox()
        self.shadow_blur_spin.setRange(0, 100)
        self.shadow_blur_spin.setValue(8)
        self.shadow_blur_spin.setSuffix(" px")
        self.shadow_blur_spin.setEnabled(False)
        style_form.addRow("Shadow blur", self.shadow_blur_spin)

        shadow_offset_row = QWidget()
        shadow_offset_layout = QHBoxLayout(shadow_offset_row)
        shadow_offset_layout.setContentsMargins(0, 0, 0, 0)

        self.shadow_offset_x_spin = QSpinBox()
        self.shadow_offset_x_spin.setRange(-100, 100)
        self.shadow_offset_x_spin.setValue(3)
        self.shadow_offset_x_spin.setPrefix("X ")
        self.shadow_offset_x_spin.setEnabled(False)

        self.shadow_offset_y_spin = QSpinBox()
        self.shadow_offset_y_spin.setRange(-100, 100)
        self.shadow_offset_y_spin.setValue(3)
        self.shadow_offset_y_spin.setPrefix("Y ")
        self.shadow_offset_y_spin.setEnabled(False)

        shadow_offset_layout.addWidget(self.shadow_offset_x_spin)
        shadow_offset_layout.addWidget(self.shadow_offset_y_spin)
        style_form.addRow("Shadow offset", shadow_offset_row)

        editor_form.addRow(style_group)

        right_layout.addWidget(editor_group)

        self.splitter.addWidget(self.clip_panel)
        self.splitter.addWidget(center)
        self.splitter.addWidget(self.text_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setSizes([260, 760, 330])

        root.addWidget(self.splitter)

        export_group = QGroupBox("Final export")
        export_layout = QVBoxLayout(export_group)

        self.assembly_export_picker = DirectoryPicker(
            "Export folder",
            settings.export_dir(),
            settings.set_export_dir,
        )
        export_layout.addWidget(self.assembly_export_picker)

        export_row = QHBoxLayout()
        self.assembly_export_filename = QLineEdit("assembly.mp4")
        self.assembly_export_button = QPushButton("Export assembled video")
        self.assembly_export_button.setEnabled(False)
        self.assembly_cancel_button = QPushButton("Cancel")
        self.assembly_cancel_button.setEnabled(False)

        export_row.addWidget(QLabel("Filename"))
        export_row.addWidget(self.assembly_export_filename, 1)
        export_row.addWidget(self.assembly_export_button)
        export_row.addWidget(self.assembly_cancel_button)
        export_layout.addLayout(export_row)

        self.assembly_export_progress = QProgressBar()
        self.assembly_export_progress.setRange(0, 100)
        self.assembly_export_progress.setValue(0)
        export_layout.addWidget(self.assembly_export_progress)

        root.addWidget(export_group)

        self.status_label = QLabel("Add clips to build the assembly timeline.")
        self.status_label.setStyleSheet("color:#9aa0a6;")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        self._connect_signals()

    def _connect_signals(self) -> None:
        self.toggle_clips_button.toggled.connect(self._toggle_clip_panel)
        self.toggle_texts_button.toggled.connect(self._toggle_text_panel)

        self.add_clip_button.clicked.connect(self._add_clips)
        self.remove_clip_button.clicked.connect(self._remove_selected_clip)
        self.clip_list.itemSelectionChanged.connect(self._on_clip_selection_changed)
        self.clip_list.model().rowsMoved.connect(self._on_clip_order_changed)

        self.play_button.clicked.connect(self._toggle_playback)
        self.timeline.sliderPressed.connect(self._on_slider_pressed)
        self.timeline.sliderReleased.connect(self._on_slider_released)
        self.timeline.sliderMoved.connect(self._on_slider_moved)

        self.player.positionChanged.connect(self._on_player_position_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.errorOccurred.connect(self._on_player_error)

        self.preview.createTextRequested.connect(self._create_text_at)
        self.preview.overlayMoved.connect(self._on_overlay_moved)
        self.preview.overlaySelected.connect(self._select_overlay_by_id)
        self.preview.overlayTextEdited.connect(self._on_preview_text_edited)

        self.add_text_button.clicked.connect(self._add_text_centered)
        self.remove_text_button.clicked.connect(self._remove_selected_text)
        self.text_list.itemSelectionChanged.connect(self._on_text_selection_changed)
        self.text_editor.textChanged.connect(self._on_text_editor_changed)
        self.text_start_edit.editingFinished.connect(self._on_text_start_edited)
        self.text_end_edit.editingFinished.connect(self._on_text_end_edited)
        self.set_text_start_button.clicked.connect(self._set_text_start_from_playhead)
        self.set_text_end_button.clicked.connect(self._set_text_end_from_playhead)

        self.font_combo.currentFontChanged.connect(
            lambda _font: self._on_style_changed()
        )
        self.font_size_spin.valueChanged.connect(
            lambda _value: self._on_style_changed()
        )
        self.text_color_button.colorChanged.connect(
            lambda _color: self._on_style_changed()
        )
        self.background_enabled_check.toggled.connect(
            lambda _checked: self._on_style_changed()
        )
        self.background_color_button.colorChanged.connect(
            lambda _color: self._on_style_changed()
        )
        self.background_opacity_spin.valueChanged.connect(
            lambda _value: self._on_style_changed()
        )
        self.background_padding_spin.valueChanged.connect(
            lambda _value: self._on_style_changed()
        )
        self.outline_enabled_check.toggled.connect(
            lambda _checked: self._on_style_changed()
        )
        self.outline_color_button.colorChanged.connect(
            lambda _color: self._on_style_changed()
        )
        self.outline_width_spin.valueChanged.connect(
            lambda _value: self._on_style_changed()
        )
        self.shadow_enabled_check.toggled.connect(
            lambda _checked: self._on_style_changed()
        )
        self.shadow_color_button.colorChanged.connect(
            lambda _color: self._on_style_changed()
        )
        self.shadow_opacity_spin.valueChanged.connect(
            lambda _value: self._on_style_changed()
        )
        self.shadow_blur_spin.valueChanged.connect(
            lambda _value: self._on_style_changed()
        )
        self.shadow_offset_x_spin.valueChanged.connect(
            lambda _value: self._on_style_changed()
        )
        self.shadow_offset_y_spin.valueChanged.connect(
            lambda _value: self._on_style_changed()
        )

        self.assembly_export_button.clicked.connect(
            self._start_assembly_export
        )
        self.assembly_cancel_button.clicked.connect(
            self._cancel_assembly_export
        )

    def _toggle_clip_panel(self, visible: bool) -> None:
        self.clip_panel.setVisible(visible)
        self.toggle_clips_button.setText("Hide clips" if visible else "Show clips")

    def _toggle_text_panel(self, visible: bool) -> None:
        self.text_panel.setVisible(visible)
        self.toggle_texts_button.setText(
            "Hide text panel" if visible else "Show text panel"
        )

    def _add_clips(self) -> None:
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Add clips",
            self._settings.input_dir(),
            VIDEO_FILTER,
        )
        if not filenames:
            return

        self._settings.set_input_dir(str(Path(filenames[0]).parent))

        added = 0
        for filename in filenames:
            path = Path(filename)
            try:
                duration_ms = probe_duration_ms(path)
            except (OSError, RuntimeError) as exc:
                QMessageBox.warning(
                    self,
                    "Add clip",
                    f"Could not read {path.name}:\n{exc}",
                )
                continue

            clip = {
                "id": uuid4().hex,
                "path": str(path),
                "duration_ms": duration_ms,
            }
            self.clip_list.addItem(self._build_clip_item(clip))
            added += 1

        if added:
            self._rebuild_timeline()
            self._mark_project_changed()
            self.status_label.setText(f"Added {added} clip(s).")

    def _build_clip_item(self, clip: Dict[str, Any]) -> QListWidgetItem:
        path = Path(str(clip.get("path", "")))
        duration_ms = max(0, int(clip.get("duration_ms", 0)))
        clip_id = str(clip.get("id") or uuid4().hex)

        data = {
            "id": clip_id,
            "path": str(path),
            "duration_ms": duration_ms,
        }

        label = f"{path.name}\n{format_timecode(duration_ms)}"
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, data)
        item.setToolTip(str(path))
        item.setSizeHint(QSize(230, 104))

        thumbnail = extract_thumbnail_png(path)
        if thumbnail:
            pixmap = QPixmap()
            if pixmap.loadFromData(thumbnail):
                item.setIcon(QIcon(pixmap))

        return item

    def _remove_selected_clip(self) -> None:
        row = self.clip_list.currentRow()
        if row < 0:
            return

        item = self.clip_list.item(row)
        data = item.data(Qt.UserRole)
        removed_id = str(data.get("id")) if isinstance(data, dict) else None

        self.clip_list.takeItem(row)

        if removed_id and removed_id == self._current_clip_id:
            self.player.stop()
            self.player.setSource(QUrl())
            self._current_clip_id = None
            self._pending_seek_ms = None
            self._pending_autoplay = False
            self._continuous_playback = False

        self._rebuild_timeline()
        self._clamp_overlay_times_to_timeline()
        self._rebuild_text_list()
        self._mark_project_changed()
        self.status_label.setText("Clip removed.")

    def _on_clip_selection_changed(self) -> None:
        row = self.clip_list.currentRow()
        if row < 0 or row >= len(self._spans):
            return

        span = self._spans[row]
        self._continuous_playback = False
        self._set_global_position(span.start_ms, autoplay=False)

    def _on_clip_order_changed(self, *args) -> None:
        self._rebuild_timeline()
        self._clamp_overlay_times_to_timeline()
        self._rebuild_text_list()
        self._mark_project_changed()
        self.status_label.setText("Clip order updated.")

    def _rebuild_timeline(self) -> None:
        durations = []
        for row in range(self.clip_list.count()):
            data = self._clip_data(row)
            durations.append(max(0, int(data.get("duration_ms", 0))))

        self._spans = build_clip_spans(durations)
        total = total_duration_ms(self._spans)
        self.timeline.setRange(0, total)
        self.timeline.setEnabled(bool(self._spans))
        self.play_button.setEnabled(bool(self._spans))
        self.add_text_button.setEnabled(bool(self._spans))
        self._update_assembly_export_enabled()

        if not self._spans:
            self.timeline.setValue(0)
            self.time_label.setText("00:00.000 / 00:00.000")
            self.player.stop()
            self.player.setSource(QUrl())
            self._current_clip_id = None
            self.preview.set_current_time(0, self._text_overlays)
            return

        current_span = self._current_span()
        if current_span is not None:
            global_position = min(
                current_span.end_ms,
                current_span.start_ms + max(0, self.player.position()),
            )
        else:
            global_position = min(self.timeline.value(), total)

        self.timeline.setValue(global_position)
        self._update_global_time(global_position)

    def _clip_data(self, row: int) -> Dict[str, Any]:
        item = self.clip_list.item(row)
        data = item.data(Qt.UserRole) if item is not None else None
        if isinstance(data, dict):
            return data
        return {}

    def _row_for_clip_id(self, clip_id: Optional[str]) -> int:
        if not clip_id:
            return -1
        for row in range(self.clip_list.count()):
            if str(self._clip_data(row).get("id")) == clip_id:
                return row
        return -1

    def _current_span(self) -> Optional[ClipSpan]:
        row = self._row_for_clip_id(self._current_clip_id)
        if 0 <= row < len(self._spans):
            return self._spans[row]
        return None

    def _toggle_playback(self) -> None:
        if not self._spans:
            return

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._continuous_playback = False
            self.player.pause()
            return

        self._continuous_playback = True
        global_position = self.timeline.value()
        total = total_duration_ms(self._spans)
        if global_position >= total:
            global_position = 0
        self._set_global_position(global_position, autoplay=True)

    def _set_global_position(self, global_ms: int, autoplay: bool) -> None:
        located = locate_global_position(self._spans, global_ms)
        if located is None:
            return

        span, local_ms = located
        data = self._clip_data(span.index)
        path = Path(str(data.get("path", "")))
        clip_id = str(data.get("id", ""))

        if not path.is_file():
            self.status_label.setText(f"Missing clip: {path}")
            return

        global_ms = min(total_duration_ms(self._spans), max(0, int(global_ms)))
        self.timeline.setValue(global_ms)
        self._update_global_time(global_ms)

        current_row = self._row_for_clip_id(self._current_clip_id)
        same_clip = self._current_clip_id == clip_id and current_row == span.index

        if same_clip and not self.player.source().isEmpty():
            self.player.setPosition(local_ms)
            if autoplay:
                self.player.play()
            return

        self._current_clip_id = clip_id
        self._pending_seek_ms = local_ms
        self._pending_autoplay = autoplay

        self.clip_list.blockSignals(True)
        self.clip_list.setCurrentRow(span.index)
        self.clip_list.blockSignals(False)

        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.status_label.setText(
            f"Clip {span.index + 1}/{len(self._spans)}: {path.name}"
        )

    def _on_media_status_changed(
        self,
        status: QMediaPlayer.MediaStatus,
    ) -> None:
        if status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ):
            if self._pending_seek_ms is not None:
                position = self._pending_seek_ms
                self._pending_seek_ms = None
                self.player.setPosition(position)

            if self._pending_autoplay:
                self._pending_autoplay = False
                self.player.play()

        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if not self._continuous_playback:
                return

            row = self._row_for_clip_id(self._current_clip_id)
            next_row = row + 1
            if 0 <= next_row < len(self._spans):
                self._set_global_position(
                    self._spans[next_row].start_ms,
                    autoplay=True,
                )
            else:
                self._continuous_playback = False
                total = total_duration_ms(self._spans)
                self.timeline.setValue(total)
                self._update_global_time(total)

    def _on_playback_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
    ) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setText("Pause")
        else:
            self.play_button.setText("Play")

    def _on_player_position_changed(self, local_ms: int) -> None:
        span = self._current_span()
        if span is None or self._slider_is_being_dragged:
            return

        global_ms = min(
            span.end_ms,
            span.start_ms + max(0, int(local_ms)),
        )
        self.timeline.setValue(global_ms)
        self._update_global_time(global_ms)

    def _on_slider_pressed(self) -> None:
        self._slider_is_being_dragged = True
        self._was_playing_before_seek = (
            self.player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        )
        if self._was_playing_before_seek:
            self.player.pause()

    def _on_slider_moved(self, value: int) -> None:
        self._update_global_time(value)

    def _on_slider_released(self) -> None:
        self._slider_is_being_dragged = False
        self._continuous_playback = self._was_playing_before_seek
        self._set_global_position(
            self.timeline.value(),
            autoplay=self._was_playing_before_seek,
        )

    def _update_global_time(self, global_ms: int) -> None:
        self.time_label.setText(
            f"{format_timecode(global_ms)} / "
            f"{format_timecode(total_duration_ms(self._spans))}"
        )
        self.preview.set_current_time(global_ms, self._text_overlays)

    def _create_text_at(self, x_norm: float, y_norm: float) -> None:
        if not self._spans:
            return
        overlay = self._new_overlay(x_norm, y_norm)
        self._text_overlays.append(overlay)
        self._text_overlays = sort_text_overlays(self._text_overlays)
        self._rebuild_text_list(overlay["id"])
        self.preview.sync_overlays(
            self._text_overlays,
            self.timeline.value(),
        )
        self.preview.begin_editing_overlay(overlay["id"])
        self._mark_project_changed()
        self.status_label.setText("Text overlay added. Type directly on the preview.")

    def _add_text_centered(self) -> None:
        self._create_text_at(0.5, 0.5)

    def _new_overlay(self, x_norm: float, y_norm: float) -> Dict[str, Any]:
        total = total_duration_ms(self._spans)
        current = min(total, max(0, self.timeline.value()))

        if current >= total and total > 0:
            end_ms = total
            start_ms = max(0, total - 3000)
        else:
            start_ms = current
            end_ms = min(total, start_ms + 3000)
            if end_ms <= start_ms:
                end_ms = min(total, start_ms + 1000)

        return normalize_text_overlay(
            {
                "id": uuid4().hex,
                "text": "Text",
                "start_ms": start_ms,
                "end_ms": end_ms,
                "x_norm": x_norm,
                "y_norm": y_norm,
            },
            total,
        )

    def _overlay_by_id(self, overlay_id: str) -> Optional[Dict[str, Any]]:
        for overlay in self._text_overlays:
            if str(overlay.get("id")) == overlay_id:
                return overlay
        return None

    def _selected_overlay_id(self) -> Optional[str]:
        item = self.text_list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _select_overlay_by_id(self, overlay_id: str) -> None:
        for row in range(self.text_list.count()):
            item = self.text_list.item(row)
            if str(item.data(Qt.UserRole)) == overlay_id:
                self.text_list.blockSignals(True)
                self.text_list.setCurrentRow(row)
                self.text_list.blockSignals(False)
                self._populate_text_editor(overlay_id)
                self.preview.select_overlay(overlay_id)
                return

    def _on_text_selection_changed(self) -> None:
        overlay_id = self._selected_overlay_id()
        self._set_text_controls_enabled(overlay_id is not None)
        if overlay_id is None:
            self._clear_text_editor()
            return

        self._populate_text_editor(overlay_id)
        self.preview.select_overlay(overlay_id)

    def _populate_text_editor(self, overlay_id: str) -> None:
        overlay = self._overlay_by_id(overlay_id)
        if overlay is None:
            return

        self._set_text_controls_enabled(True)

        self.text_editor.blockSignals(True)
        self.text_editor.setPlainText(str(overlay.get("text", "")))
        self.text_editor.blockSignals(False)

        self.text_start_edit.blockSignals(True)
        self.text_end_edit.blockSignals(True)
        self.text_start_edit.setText(
            format_timecode(int(overlay.get("start_ms", 0)))
        )
        self.text_end_edit.setText(
            format_timecode(int(overlay.get("end_ms", 0)))
        )
        self.text_start_edit.blockSignals(False)
        self.text_end_edit.blockSignals(False)

        self.text_position_label.setText(
            f"x {float(overlay.get('x_norm', 0.0)):.3f}, "
            f"y {float(overlay.get('y_norm', 0.0)):.3f}"
        )

        style_controls = [
            self.font_combo,
            self.font_size_spin,
            self.text_color_button,
            self.background_enabled_check,
            self.background_color_button,
            self.background_opacity_spin,
            self.background_padding_spin,
            self.outline_enabled_check,
            self.outline_color_button,
            self.outline_width_spin,
            self.shadow_enabled_check,
            self.shadow_color_button,
            self.shadow_opacity_spin,
            self.shadow_blur_spin,
            self.shadow_offset_x_spin,
            self.shadow_offset_y_spin,
        ]
        for control in style_controls:
            control.blockSignals(True)

        try:
            self.font_combo.setCurrentFont(
                QFont(str(overlay.get("font_family", "Arial")))
            )
            self.font_size_spin.setValue(
                int(overlay.get("font_size", 28))
            )
            self.text_color_button.set_color(
                str(overlay.get("text_color", "#ffffff"))
            )
            self.background_enabled_check.setChecked(
                bool(overlay.get("background_enabled", False))
            )
            self.background_color_button.set_color(
                str(overlay.get("background_color", "#000000"))
            )
            self.background_opacity_spin.setValue(
                round(
                    int(overlay.get("background_opacity", 170))
                    * 100
                    / 255
                )
            )
            self.background_padding_spin.setValue(
                int(overlay.get("background_padding", 8))
            )
            self.outline_enabled_check.setChecked(
                bool(overlay.get("outline_enabled", False))
            )
            self.outline_color_button.set_color(
                str(overlay.get("outline_color", "#000000"))
            )
            self.outline_width_spin.setValue(
                int(overlay.get("outline_width", 2))
            )
            self.shadow_enabled_check.setChecked(
                bool(overlay.get("shadow_enabled", False))
            )
            self.shadow_color_button.set_color(
                str(overlay.get("shadow_color", "#000000"))
            )
            self.shadow_opacity_spin.setValue(
                round(
                    int(overlay.get("shadow_opacity", 160))
                    * 100
                    / 255
                )
            )
            self.shadow_blur_spin.setValue(
                int(overlay.get("shadow_blur", 8))
            )
            self.shadow_offset_x_spin.setValue(
                int(overlay.get("shadow_offset_x", 3))
            )
            self.shadow_offset_y_spin.setValue(
                int(overlay.get("shadow_offset_y", 3))
            )
        finally:
            for control in style_controls:
                control.blockSignals(False)

    def _clear_text_editor(self) -> None:
        self.text_editor.blockSignals(True)
        self.text_editor.clear()
        self.text_editor.blockSignals(False)
        self.text_start_edit.setText("00:00.000")
        self.text_end_edit.setText("00:00.000")
        self.text_position_label.setText("Position: -")

        self.font_combo.setCurrentFont(QFont("Arial"))
        self.font_size_spin.setValue(28)
        self.text_color_button.set_color("#ffffff")
        self.background_enabled_check.setChecked(False)
        self.background_color_button.set_color("#000000")
        self.background_opacity_spin.setValue(67)
        self.background_padding_spin.setValue(8)
        self.outline_enabled_check.setChecked(False)
        self.outline_color_button.set_color("#000000")
        self.outline_width_spin.setValue(2)
        self.shadow_enabled_check.setChecked(False)
        self.shadow_color_button.set_color("#000000")
        self.shadow_opacity_spin.setValue(63)
        self.shadow_blur_spin.setValue(8)
        self.shadow_offset_x_spin.setValue(3)
        self.shadow_offset_y_spin.setValue(3)

        self._set_text_controls_enabled(False)

    def _set_text_controls_enabled(self, enabled: bool) -> None:
        self.text_editor.setEnabled(enabled)
        self.remove_text_button.setEnabled(enabled)
        self.text_start_edit.setEnabled(enabled)
        self.text_end_edit.setEnabled(enabled)
        self.set_text_start_button.setEnabled(enabled)
        self.set_text_end_button.setEnabled(enabled)
        self.font_combo.setEnabled(enabled)
        self.font_size_spin.setEnabled(enabled)
        self.text_color_button.setEnabled(enabled)
        self.background_enabled_check.setEnabled(enabled)
        self.background_color_button.setEnabled(enabled)
        self.background_opacity_spin.setEnabled(enabled)
        self.background_padding_spin.setEnabled(enabled)
        self.outline_enabled_check.setEnabled(enabled)
        self.outline_color_button.setEnabled(enabled)
        self.outline_width_spin.setEnabled(enabled)
        self.shadow_enabled_check.setEnabled(enabled)
        self.shadow_color_button.setEnabled(enabled)
        self.shadow_opacity_spin.setEnabled(enabled)
        self.shadow_blur_spin.setEnabled(enabled)
        self.shadow_offset_x_spin.setEnabled(enabled)
        self.shadow_offset_y_spin.setEnabled(enabled)

    def _on_style_changed(self) -> None:
        overlay_id = self._selected_overlay_id()
        overlay = self._overlay_by_id(overlay_id or "")
        if overlay is None:
            return

        overlay["font_family"] = self.font_combo.currentFont().family()
        overlay["font_size"] = self.font_size_spin.value()
        overlay["text_color"] = self.text_color_button.color()

        overlay["background_enabled"] = (
            self.background_enabled_check.isChecked()
        )
        overlay["background_color"] = self.background_color_button.color()
        overlay["background_opacity"] = round(
            self.background_opacity_spin.value() * 255 / 100
        )
        overlay["background_padding"] = (
            self.background_padding_spin.value()
        )

        overlay["outline_enabled"] = (
            self.outline_enabled_check.isChecked()
        )
        overlay["outline_color"] = self.outline_color_button.color()
        overlay["outline_width"] = self.outline_width_spin.value()

        overlay["shadow_enabled"] = (
            self.shadow_enabled_check.isChecked()
        )
        overlay["shadow_color"] = self.shadow_color_button.color()
        overlay["shadow_opacity"] = round(
            self.shadow_opacity_spin.value() * 255 / 100
        )
        overlay["shadow_blur"] = self.shadow_blur_spin.value()
        overlay["shadow_offset_x"] = self.shadow_offset_x_spin.value()
        overlay["shadow_offset_y"] = self.shadow_offset_y_spin.value()

        self.preview.sync_overlays(
            self._text_overlays,
            self.timeline.value(),
        )
        self._mark_project_changed()

    def _on_text_editor_changed(self) -> None:
        overlay_id = self._selected_overlay_id()
        overlay = self._overlay_by_id(overlay_id or "")
        if overlay is None:
            return

        overlay["text"] = self.text_editor.toPlainText()
        self._refresh_text_list_label(overlay_id)
        self.preview.sync_overlays(self._text_overlays, self.timeline.value())
        self._mark_project_changed()

    def _on_preview_text_edited(self, overlay_id: str, text: str) -> None:
        overlay = self._overlay_by_id(overlay_id)
        if overlay is None:
            return

        overlay["text"] = text
        self._refresh_text_list_label(overlay_id)

        if self._selected_overlay_id() == overlay_id:
            self.text_editor.blockSignals(True)
            self.text_editor.setPlainText(text)
            self.text_editor.blockSignals(False)

        self._mark_project_changed()

    def _on_overlay_moved(
        self,
        overlay_id: str,
        x_norm: float,
        y_norm: float,
    ) -> None:
        overlay = self._overlay_by_id(overlay_id)
        if overlay is None:
            return

        overlay["x_norm"] = min(1.0, max(0.0, float(x_norm)))
        overlay["y_norm"] = min(1.0, max(0.0, float(y_norm)))

        if self._selected_overlay_id() == overlay_id:
            self.text_position_label.setText(
                f"x {overlay['x_norm']:.3f}, y {overlay['y_norm']:.3f}"
            )

        self._mark_project_changed()

    def _remove_selected_text(self) -> None:
        overlay_id = self._selected_overlay_id()
        if overlay_id is None:
            return

        self._text_overlays = [
            item
            for item in self._text_overlays
            if str(item.get("id")) != overlay_id
        ]
        self._rebuild_text_list()
        self.preview.sync_overlays(self._text_overlays, self.timeline.value())
        self._clear_text_editor()
        self._mark_project_changed()
        self.status_label.setText("Text overlay removed.")

    def _on_text_start_edited(self) -> None:
        overlay_id = self._selected_overlay_id()
        overlay = self._overlay_by_id(overlay_id or "")
        if overlay is None:
            return

        try:
            value = parse_timecode(self.text_start_edit.text())
        except ValueError:
            self.status_label.setText("Invalid text start time.")
            self._populate_text_editor(overlay_id)
            return

        end_ms = int(overlay.get("end_ms", 0))
        total = total_duration_ms(self._spans)
        if value < 0 or value > total or value > end_ms:
            self.status_label.setText("Text start must be within the timeline and before End.")
            self._populate_text_editor(overlay_id)
            return

        overlay["start_ms"] = value
        self._text_overlays = sort_text_overlays(self._text_overlays)
        self._rebuild_text_list(overlay_id)
        self.preview.sync_overlays(self._text_overlays, self.timeline.value())
        self._mark_project_changed()

    def _on_text_end_edited(self) -> None:
        overlay_id = self._selected_overlay_id()
        overlay = self._overlay_by_id(overlay_id or "")
        if overlay is None:
            return

        try:
            value = parse_timecode(self.text_end_edit.text())
        except ValueError:
            self.status_label.setText("Invalid text end time.")
            self._populate_text_editor(overlay_id)
            return

        start_ms = int(overlay.get("start_ms", 0))
        total = total_duration_ms(self._spans)
        if value < start_ms or value > total:
            self.status_label.setText("Text End must be after Start and within the timeline.")
            self._populate_text_editor(overlay_id)
            return

        overlay["end_ms"] = value
        self._refresh_text_list_label(overlay_id)
        self.preview.sync_overlays(self._text_overlays, self.timeline.value())
        self._mark_project_changed()

    def _set_text_start_from_playhead(self) -> None:
        overlay_id = self._selected_overlay_id()
        overlay = self._overlay_by_id(overlay_id or "")
        if overlay is None:
            return

        current = self.timeline.value()
        if current > int(overlay.get("end_ms", 0)):
            self.status_label.setText("Playhead is after this text overlay's End.")
            return

        overlay["start_ms"] = current
        self._text_overlays = sort_text_overlays(self._text_overlays)
        self._rebuild_text_list(overlay_id)
        self.preview.sync_overlays(self._text_overlays, current)
        self._mark_project_changed()

    def _set_text_end_from_playhead(self) -> None:
        overlay_id = self._selected_overlay_id()
        overlay = self._overlay_by_id(overlay_id or "")
        if overlay is None:
            return

        current = self.timeline.value()
        if current < int(overlay.get("start_ms", 0)):
            self.status_label.setText("Playhead is before this text overlay's Start.")
            return

        overlay["end_ms"] = current
        self._populate_text_editor(overlay_id)
        self._refresh_text_list_label(overlay_id)
        self.preview.sync_overlays(self._text_overlays, current)
        self._mark_project_changed()

    def _rebuild_text_list(self, selected_id: Optional[str] = None) -> None:
        if selected_id is None:
            selected_id = self._selected_overlay_id()

        self.text_list.blockSignals(True)
        self.text_list.clear()

        for overlay in sort_text_overlays(self._text_overlays):
            item = QListWidgetItem(self._overlay_list_label(overlay))
            item.setData(Qt.UserRole, str(overlay.get("id")))
            self.text_list.addItem(item)
            if str(overlay.get("id")) == selected_id:
                self.text_list.setCurrentItem(item)

        self.text_list.blockSignals(False)

        if selected_id:
            self._populate_text_editor(selected_id)
        else:
            self._clear_text_editor()

    def _refresh_text_list_label(self, overlay_id: str) -> None:
        overlay = self._overlay_by_id(overlay_id)
        if overlay is None:
            return

        for row in range(self.text_list.count()):
            item = self.text_list.item(row)
            if str(item.data(Qt.UserRole)) == overlay_id:
                item.setText(self._overlay_list_label(overlay))
                return

    @staticmethod
    def _overlay_list_label(overlay: Dict[str, Any]) -> str:
        text = str(overlay.get("text", "")).replace("\n", " ").strip()
        if len(text) > 48:
            text = text[:45] + "..."
        return (
            f"{format_timecode(int(overlay.get('start_ms', 0)))} - "
            f"{format_timecode(int(overlay.get('end_ms', 0)))}\n{text}"
        )

    def _clamp_overlay_times_to_timeline(self) -> None:
        total = total_duration_ms(self._spans)
        self._text_overlays = [
            normalize_text_overlay(item, total)
            for item in self._text_overlays
        ]

    def _start_assembly_export(self) -> None:
        if self._assembly_export_job is not None:
            return

        clips = []
        for row in range(self.clip_list.count()):
            data = self._clip_data(row)
            if data:
                clips.append(deepcopy(data))

        if not clips:
            QMessageBox.warning(
                self,
                "Final export",
                "Add at least one clip before exporting.",
            )
            return

        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            QMessageBox.critical(
                self,
                "FFmpeg not found",
                "FFmpeg was not found. Place ffmpeg.exe in "
                "tools\\ffmpeg\\ or make it available on PATH.",
            )
            return

        output_dir = Path(self.assembly_export_picker.path())
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Final export",
                f"Could not create the export folder:\n{exc}",
            )
            return

        filename = self.assembly_export_filename.text().strip()
        if not filename:
            QMessageBox.warning(
                self,
                "Final export",
                "Enter an output filename.",
            )
            return

        output_path = output_dir / filename
        if output_path.suffix == "":
            output_path = output_path.with_suffix(".mp4")
            self.assembly_export_filename.setText(output_path.name)

        if output_path.exists():
            answer = QMessageBox.question(
                self,
                "Overwrite export?",
                f"{output_path.name} already exists. Overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        try:
            job = AssemblyExportJob(
                ffmpeg_path,
                clips,
                sort_text_overlays(self._text_overlays),
                output_path,
                parent=self,
            )
        except (OSError, RuntimeError, ValueError, FileNotFoundError) as exc:
            QMessageBox.critical(
                self,
                "Final export",
                f"Could not prepare the export:\n{exc}",
            )
            return

        self._assembly_export_job = job
        self._assembly_export_output = output_path
        self.assembly_export_progress.setValue(0)
        self._update_assembly_export_enabled()
        self.assembly_cancel_button.setEnabled(True)

        job.progressChanged.connect(
            self.assembly_export_progress.setValue
        )
        job.statusChanged.connect(self.status_label.setText)
        job.finished.connect(self._on_assembly_export_finished)
        job.start()

        self.status_label.setText(
            f"Rendering {job.output_width}x{job.output_height} "
            f"at {job.output_fps:.3f} FPS..."
        )

    def _cancel_assembly_export(self) -> None:
        if self._assembly_export_job is None:
            return
        self.assembly_cancel_button.setEnabled(False)
        self._assembly_export_job.cancel()

    def _on_assembly_export_finished(
        self,
        success: bool,
        message: str,
    ) -> None:
        output_path = self._assembly_export_output
        self._assembly_export_job = None
        self._assembly_export_output = None
        self.assembly_cancel_button.setEnabled(False)
        self._update_assembly_export_enabled()

        if success:
            self.status_label.setText(
                f"Final export completed: {output_path}"
            )
            QMessageBox.information(
                self,
                "Final export completed",
                f"Video saved to:\n{output_path}",
            )
        else:
            self.status_label.setText(message.splitlines()[0])
            if message != "Assembly export cancelled.":
                QMessageBox.critical(
                    self,
                    "Final export failed",
                    message,
                )

    def _update_assembly_export_enabled(self) -> None:
        self.assembly_export_button.setEnabled(
            bool(self._spans)
            and self._assembly_export_job is None
        )

    def is_exporting(self) -> bool:
        return self._assembly_export_job is not None

    def cancel_export(self) -> None:
        self._cancel_assembly_export()

    def _on_player_error(
        self,
        error: QMediaPlayer.Error,
        error_string: str,
    ) -> None:
        if error == QMediaPlayer.Error.NoError:
            return
        message = error_string or self.player.errorString() or "Unknown media error"
        self.status_label.setText(f"Playback error: {message}")

    def project_state(self) -> Dict[str, Any]:
        clips = []
        for row in range(self.clip_list.count()):
            data = self._clip_data(row)
            if data:
                clips.append(deepcopy(data))

        return {
            "clips": clips,
            "text_overlays": sort_text_overlays(self._text_overlays),
        }

    def load_project_state(self, state: Dict[str, Any]) -> None:
        self._restoring_project = True
        try:
            self.clear_project()

            for raw_clip in state.get("clips", []):
                if not isinstance(raw_clip, dict):
                    continue

                path = Path(str(raw_clip.get("path", "")))
                if not path.is_file():
                    continue

                duration_ms = int(raw_clip.get("duration_ms", 0))
                if duration_ms <= 0:
                    try:
                        duration_ms = probe_duration_ms(path)
                    except (OSError, RuntimeError):
                        continue

                clip = {
                    "id": str(raw_clip.get("id") or uuid4().hex),
                    "path": str(path),
                    "duration_ms": duration_ms,
                }
                self.clip_list.addItem(self._build_clip_item(clip))

            self._rebuild_timeline()
            total = total_duration_ms(self._spans)
            self._text_overlays = [
                normalize_text_overlay(item, total)
                for item in state.get("text_overlays", [])
                if isinstance(item, dict)
            ]
            self._text_overlays = sort_text_overlays(self._text_overlays)
            self._rebuild_text_list()
            self.preview.sync_overlays(self._text_overlays, 0)
        finally:
            self._restoring_project = False

    def clear_project(self) -> None:
        self.player.stop()
        self.player.setSource(QUrl())
        self.clip_list.clear()
        self.text_list.clear()
        self._text_overlays = []
        self._spans = []
        self._current_clip_id = None
        self._pending_seek_ms = None
        self._pending_autoplay = False
        self._continuous_playback = False
        self.timeline.setRange(0, 0)
        self.timeline.setValue(0)
        self.timeline.setEnabled(False)
        self.play_button.setEnabled(False)
        self.add_text_button.setEnabled(False)
        self.assembly_export_progress.setValue(0)
        self._update_assembly_export_enabled()
        self.play_button.setText("Play")
        self.time_label.setText("00:00.000 / 00:00.000")
        self.preview.sync_overlays([], 0)
        self._clear_text_editor()
        self.status_label.setText("Add clips to build the assembly timeline.")

    def _mark_project_changed(self) -> None:
        if not self._restoring_project:
            self.projectChanged.emit()
