from pathlib import Path
from typing import Optional, Tuple
from uuid import uuid4

from PySide6.QtCore import QElapsedTimer, QRect, QTimer
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.gui.widgets.capture_frame import CaptureFrame
from src.gui.widgets.path_picker import DirectoryPicker
from src.services.ffmpeg_export import find_ffmpeg
from src.services.linux_screen_capture import (
    GnomeWaylandRecordingJob,
    X11RecordingJob,
    build_x11grab_arguments,
    check_ffmpeg_x11grab,
    check_gnome_screencast_area,
    detect_linux_session,
    qt_rect_to_x11_region,
)
from src.settings import AppSettings
from src.utils.capture_geometry import (
    PRESETS,
    logical_rect_to_physical,
    physical_size_to_logical,
    preset_by_name,
)


class RecorderTab(QWidget):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._screens = []
        self._updating_dimensions = False
        self._recording_job = None
        self._recording_output: Optional[Path] = None
        self._pending_launch = None

        self._elapsed_timer = QElapsedTimer()
        self._recording_clock = QTimer(self)
        self._recording_clock.setInterval(250)
        self._recording_clock.timeout.connect(self._update_recording_clock)

        self._start_delay = QTimer(self)
        self._start_delay.setSingleShot(True)
        self._start_delay.setInterval(300)
        self._start_delay.timeout.connect(self._launch_pending_recording)

        self.capture_frame = CaptureFrame(self)
        self.capture_frame.geometryChanged.connect(
            self._on_frame_geometry_changed
        )

        root = QVBoxLayout(self)

        backend_group = QGroupBox("Linux capture backend")
        backend_layout = QFormLayout(backend_group)
        self.session_label = QLabel("-")
        self.backend_label = QLabel("-")
        self.backend_label.setWordWrap(True)
        self.refresh_backend_button = QPushButton("Refresh backend")
        backend_layout.addRow("Session", self.session_label)
        backend_layout.addRow("Backend", self.backend_label)
        backend_layout.addRow(self.refresh_backend_button)
        root.addWidget(backend_group)

        capture_group = QGroupBox("Capture area")
        form = QFormLayout(capture_group)

        monitor_row = QWidget()
        monitor_layout = QHBoxLayout(monitor_row)
        monitor_layout.setContentsMargins(0, 0, 0, 0)
        self.monitor_combo = QComboBox()
        self.refresh_monitors_button = QPushButton("Refresh")
        monitor_layout.addWidget(self.monitor_combo, 1)
        monitor_layout.addWidget(self.refresh_monitors_button)
        form.addRow("Monitor", monitor_row)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([preset.name for preset in PRESETS])
        form.addRow("Preset", self.mode_combo)

        custom_row = QWidget()
        custom_layout = QHBoxLayout(custom_row)
        custom_layout.setContentsMargins(0, 0, 0, 0)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 16384)
        self.width_spin.setValue(1920)
        self.width_spin.setSuffix(" px")

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 16384)
        self.height_spin.setValue(1080)
        self.height_spin.setSuffix(" px")

        custom_layout.addWidget(QLabel("Width"))
        custom_layout.addWidget(self.width_spin)
        custom_layout.addWidget(QLabel("Height"))
        custom_layout.addWidget(self.height_spin)
        custom_layout.addStretch(1)
        form.addRow("Capture size", custom_row)

        frame_buttons = QWidget()
        frame_buttons_layout = QHBoxLayout(frame_buttons)
        frame_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.show_area_button = QPushButton("Show / position capture frame")
        self.hide_area_button = QPushButton("Hide frame")
        frame_buttons_layout.addWidget(self.show_area_button)
        frame_buttons_layout.addWidget(self.hide_area_button)
        frame_buttons_layout.addStretch(1)
        form.addRow(frame_buttons)

        self.logical_geometry_label = QLabel("Logical frame: -")
        self.physical_geometry_label = QLabel("Physical capture: -")
        self.monitor_info_label = QLabel("Monitor: -")
        self.monitor_info_label.setWordWrap(True)
        form.addRow("Qt / Wayland", self.logical_geometry_label)
        form.addRow("Physical pixels", self.physical_geometry_label)
        form.addRow("Display info", self.monitor_info_label)

        self.capture_help_label = QLabel(
            "Drag inside the red frame to move it. Aspect-ratio presets "
            "can be resized from the bottom-right red handle. "
            "Press Esc to hide the frame. The frame is hidden before recording."
        )
        self.capture_help_label.setWordWrap(True)
        self.capture_help_label.setStyleSheet("color:#9aa0a6;")
        form.addRow("", self.capture_help_label)

        root.addWidget(capture_group)

        output_group = QGroupBox("Recording")
        output_layout = QVBoxLayout(output_group)

        self.output_picker = DirectoryPicker(
            "Output folder",
            settings.record_dir(),
            settings.set_record_dir,
        )
        output_layout.addWidget(self.output_picker)

        file_row = QHBoxLayout()
        self.filename_edit = QLineEdit("recording.mp4")
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["30", "60"])
        file_row.addWidget(QLabel("Filename"))
        file_row.addWidget(self.filename_edit, 1)
        file_row.addWidget(QLabel("FPS"))
        file_row.addWidget(self.fps_combo)
        output_layout.addLayout(file_row)

        record_row = QHBoxLayout()
        self.start_button = QPushButton("Start recording")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.recording_time_label = QLabel("00:00:00")
        record_row.addWidget(self.start_button)
        record_row.addWidget(self.stop_button)
        record_row.addWidget(self.recording_time_label)
        record_row.addStretch(1)
        output_layout.addLayout(record_row)

        root.addWidget(output_group)

        self.status_label = QLabel(
            "Choose a monitor and position the capture frame."
        )
        self.status_label.setStyleSheet("color:#9aa0a6;")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)
        root.addStretch(1)

        self._connect_signals()
        self._refresh_backend_status()
        self._refresh_monitors()
        self._apply_preset(center=True)

    def _connect_signals(self) -> None:
        self.refresh_backend_button.clicked.connect(
            self._refresh_backend_status
        )
        self.refresh_monitors_button.clicked.connect(
            self._refresh_monitors
        )
        self.monitor_combo.currentIndexChanged.connect(
            self._on_monitor_changed
        )
        self.mode_combo.currentTextChanged.connect(
            self._on_preset_changed
        )
        self.width_spin.valueChanged.connect(
            self._on_dimension_changed
        )
        self.height_spin.valueChanged.connect(
            self._on_dimension_changed
        )
        self.show_area_button.clicked.connect(self._show_capture_frame)
        self.hide_area_button.clicked.connect(self.capture_frame.hide)
        self.start_button.clicked.connect(self._start_recording)
        self.stop_button.clicked.connect(self._stop_recording)

        app = QGuiApplication.instance()
        if app is not None:
            app.screenAdded.connect(self._on_screen_configuration_changed)
            app.screenRemoved.connect(self._on_screen_configuration_changed)

    def _refresh_backend_status(self) -> None:
        info = detect_linux_session()

        if info.is_wayland:
            self.session_label.setText(
                f"Wayland ({info.wayland_display or 'display unknown'})"
            )
            if info.gdbus_path:
                self.backend_label.setText(
                    "GNOME Shell ScreencastArea via session D-Bus. "
                    "Recording is created as WebM and converted to the "
                    "selected final format when stopped."
                )
            else:
                self.backend_label.setText(
                    "Wayland detected, but gdbus was not found."
                )
        elif info.is_x11:
            self.session_label.setText(
                f"X11 ({info.display or 'DISPLAY not set'})"
            )
            self.backend_label.setText(
                "FFmpeg x11grab direct region capture."
            )
        else:
            self.session_label.setText("Unknown graphical session")
            self.backend_label.setText(
                "Neither an X11 nor a Wayland session could be detected."
            )

    def _refresh_monitors(self) -> None:
        current_name = None
        screen = self._selected_screen()
        if screen is not None:
            current_name = screen.name()

        self._screens = list(QGuiApplication.screens())
        self.monitor_combo.blockSignals(True)
        self.monitor_combo.clear()

        primary = QGuiApplication.primaryScreen()
        selected_index = 0

        for index, screen in enumerate(self._screens):
            geometry = screen.geometry()
            dpr = max(0.01, float(screen.devicePixelRatio()))
            physical_width = round(geometry.width() * dpr)
            physical_height = round(geometry.height() * dpr)
            primary_text = " [Primary]" if screen is primary else ""

            self.monitor_combo.addItem(
                f"{index + 1}: {screen.name()} "
                f"({physical_width} x {physical_height})"
                f"{primary_text}"
            )

            if current_name and screen.name() == current_name:
                selected_index = index
            elif current_name is None and screen is primary:
                selected_index = index

        if self._screens:
            self.monitor_combo.setCurrentIndex(selected_index)

        self.monitor_combo.blockSignals(False)
        self._on_monitor_changed()

    def _selected_screen(self) -> Optional[QScreen]:
        index = self.monitor_combo.currentIndex()
        if 0 <= index < len(self._screens):
            return self._screens[index]
        return None

    def _on_screen_configuration_changed(self, *args) -> None:
        self.capture_frame.hide()
        self._refresh_monitors()

    def _on_monitor_changed(self, *args) -> None:
        self.capture_frame.hide()
        self._apply_preset(center=True)

    def _on_preset_changed(self, name: str) -> None:
        preset = preset_by_name(name)

        self._updating_dimensions = True
        try:
            if preset.is_fixed_size:
                self.width_spin.setValue(int(preset.width_px or 1))
                self.height_spin.setValue(int(preset.height_px or 1))
        finally:
            self._updating_dimensions = False

        self._apply_preset(center=False)

    def _on_dimension_changed(self, *args) -> None:
        if self._updating_dimensions:
            return

        preset = preset_by_name(self.mode_combo.currentText())
        if preset.is_fixed_size:
            self._updating_dimensions = True
            try:
                self.width_spin.setValue(int(preset.width_px or 1))
                self.height_spin.setValue(int(preset.height_px or 1))
            finally:
                self._updating_dimensions = False
            return

        if preset.aspect_ratio is not None:
            return

        self._apply_preset(center=False)

    def _apply_preset(self, center: bool) -> None:
        screen = self._selected_screen()
        if screen is None:
            self.monitor_info_label.setText("Monitor: none detected")
            self.logical_geometry_label.setText("Logical frame: -")
            self.physical_geometry_label.setText("Physical capture: -")
            return

        geometry = screen.geometry()
        dpr = max(0.01, float(screen.devicePixelRatio()))
        preset = preset_by_name(self.mode_combo.currentText())

        if preset.is_fixed_size:
            logical_width, logical_height = physical_size_to_logical(
                int(preset.width_px or 1),
                int(preset.height_px or 1),
                dpr,
            )
            resizable = False
            aspect_ratio = None
        elif preset.aspect_ratio is not None:
            current = self.capture_frame.capture_geometry()
            if current.isValid() and not current.isEmpty():
                logical_width = current.width()
                logical_height = current.height()
            else:
                logical_width = round(geometry.width() * 0.7)
                logical_height = round(geometry.height() * 0.7)
            resizable = True
            aspect_ratio = preset.aspect_ratio
        else:
            logical_width, logical_height = physical_size_to_logical(
                self.width_spin.value(),
                self.height_spin.value(),
                dpr,
            )
            resizable = False
            aspect_ratio = None

        self.capture_frame.configure(
            geometry,
            logical_width,
            logical_height,
            aspect_ratio,
            resizable,
            center=center,
        )
        self._update_monitor_info(screen)
        self._on_frame_geometry_changed(
            self.capture_frame.capture_geometry()
        )

    def _show_capture_frame(self) -> None:
        screen = self._selected_screen()
        if screen is None:
            self.status_label.setText("No monitor is available.")
            return

        self._apply_preset(center=not self.capture_frame.isVisible())
        self.capture_frame.show()
        self.capture_frame.raise_()
        self.capture_frame.activateWindow()
        self.status_label.setText(
            "Capture frame visible. Position it on the selected monitor."
        )

    def _on_frame_geometry_changed(self, rect: QRect) -> None:
        screen = self._selected_screen()
        if screen is None:
            return

        geometry = screen.geometry()
        dpr = max(0.01, float(screen.devicePixelRatio()))
        physical_x, physical_y, physical_width, physical_height = (
            logical_rect_to_physical(
                rect.x(),
                rect.y(),
                rect.width(),
                rect.height(),
                geometry.x(),
                geometry.y(),
                dpr,
            )
        )

        self.logical_geometry_label.setText(
            f"x {rect.x()}, y {rect.y()}, "
            f"{rect.width()} x {rect.height()}"
        )
        self.physical_geometry_label.setText(
            f"monitor offset x {physical_x}, y {physical_y}, "
            f"{physical_width} x {physical_height} px"
        )

        preset = preset_by_name(self.mode_combo.currentText())
        if preset.aspect_ratio is not None:
            self._updating_dimensions = True
            try:
                self.width_spin.setValue(physical_width)
                self.height_spin.setValue(physical_height)
            finally:
                self._updating_dimensions = False

        monitor_physical_width = round(geometry.width() * dpr)
        monitor_physical_height = round(geometry.height() * dpr)

        if (
            physical_width > monitor_physical_width
            or physical_height > monitor_physical_height
        ):
            self.status_label.setText(
                "Requested capture size exceeded the selected monitor and "
                "was limited to the monitor bounds."
            )
        else:
            self.status_label.setText("Capture area ready.")

    def _update_monitor_info(self, screen: QScreen) -> None:
        geometry = screen.geometry()
        dpr = max(0.01, float(screen.devicePixelRatio()))
        physical_width = round(geometry.width() * dpr)
        physical_height = round(geometry.height() * dpr)

        self.monitor_info_label.setText(
            f"{screen.name()} | "
            f"Qt {geometry.width()} x {geometry.height()} "
            f"at ({geometry.x()}, {geometry.y()}) | "
            f"DPR {dpr:.2f} | "
            f"physical {physical_width} x {physical_height}"
        )

    def _logical_capture_region(self) -> Optional[Tuple[int, int, int, int]]:
        screen = self._selected_screen()
        if screen is None:
            return None
        rect = self.capture_frame.capture_geometry()
        return rect.x(), rect.y(), rect.width(), rect.height()

    def _x11_capture_region(self) -> Optional[Tuple[int, int, int, int]]:
        screen = self._selected_screen()
        if screen is None:
            return None

        rect = self.capture_frame.capture_geometry()
        geometry = screen.geometry()
        return qt_rect_to_x11_region(
            rect.x(),
            rect.y(),
            rect.width(),
            rect.height(),
            geometry.x(),
            geometry.y(),
            float(screen.devicePixelRatio()),
        )

    def _start_recording(self) -> None:
        if self.is_recording():
            return

        session = detect_linux_session()
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            QMessageBox.critical(
                self,
                "FFmpeg not found",
                "Run ./setup_ffmpeg.sh or place the Linux ffmpeg binary "
                "in tools/ffmpeg/ffmpeg.",
            )
            return

        if session.is_x11:
            ok, details = check_ffmpeg_x11grab(ffmpeg_path)
            if not ok:
                QMessageBox.critical(
                    self,
                    "X11 capture unavailable",
                    details,
                )
                return
            region = self._x11_capture_region()
            backend = "x11"
        elif session.is_wayland:
            ok, details = check_gnome_screencast_area(
                session.gdbus_path
            )
            if not ok:
                QMessageBox.critical(
                    self,
                    "Wayland capture unavailable",
                    details
                    + "\n\nThe RHEL8 GNOME Wayland backend requires "
                    "org.gnome.Shell.Screencast.ScreencastArea.",
                )
                return
            region = self._logical_capture_region()
            backend = "wayland"
        else:
            QMessageBox.critical(
                self,
                "Screen recording",
                "No supported Linux graphical session was detected. "
                "Expected X11 or GNOME Wayland.",
            )
            return

        if region is None:
            QMessageBox.warning(
                self,
                "Screen recording",
                "No monitor/capture area is available.",
            )
            return

        output_dir = Path(self.output_picker.path())
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Screen recording",
                f"Could not create output folder:\n{exc}",
            )
            return

        filename = self.filename_edit.text().strip()
        if not filename:
            QMessageBox.warning(
                self,
                "Screen recording",
                "Enter an output filename.",
            )
            return

        output_path = output_dir / filename
        if output_path.suffix == "":
            output_path = output_path.with_suffix(".mp4")
            self.filename_edit.setText(output_path.name)

        if output_path.suffix.lower() != ".mp4":
            QMessageBox.warning(
                self,
                "Screen recording",
                "Screen Recorder currently writes MP4 output. "
                "Use a .mp4 filename.",
            )
            return

        if output_path.exists():
            answer = QMessageBox.question(
                self,
                "Overwrite recording?",
                f"{output_path.name} already exists. Overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        fps = int(self.fps_combo.currentText())
        self.capture_frame.hide()
        self._set_recording_controls(True)
        self.stop_button.setEnabled(True)
        self.status_label.setText(
            "Capture frame hidden. Starting recording..."
        )
        self._recording_output = output_path
        self._pending_launch = (
            backend,
            session,
            ffmpeg_path,
            region,
            fps,
            output_path,
        )
        self._start_delay.start()

    def _launch_pending_recording(self) -> None:
        pending = self._pending_launch
        self._pending_launch = None
        if pending is None:
            return

        backend, session, ffmpeg_path, region, fps, output_path = pending

        if backend == "x11":
            token = uuid4().hex[:8]
            partial_path = output_path.with_name(
                f".{output_path.stem}.partial-{token}{output_path.suffix}"
            )
            arguments = build_x11grab_arguments(
                partial_path,
                fps,
                session.display,
                region,
            )
            job = X11RecordingJob(
                ffmpeg_path,
                arguments,
                partial_path,
                output_path,
                parent=self,
            )
        else:
            job = GnomeWaylandRecordingJob(
                session.gdbus_path or "",
                ffmpeg_path,
                region,
                fps,
                output_path,
                parent=self,
            )

        self._recording_job = job
        job.started.connect(self._on_recording_started)
        job.statusChanged.connect(self.status_label.setText)
        job.finished.connect(self._on_recording_finished)
        job.start()

    def _on_recording_started(self) -> None:
        self._elapsed_timer.start()
        self._recording_clock.start()
        self.recording_time_label.setText("00:00:00")

    def _stop_recording(self) -> None:
        if self._pending_launch is not None:
            self._start_delay.stop()
            self._pending_launch = None
            self._recording_output = None
            self._set_recording_controls(False)
            self.status_label.setText("Recording start cancelled.")
            return

        if self._recording_job is None:
            return

        self.stop_button.setEnabled(False)
        self._recording_job.stop()

    def _on_recording_finished(
        self,
        success: bool,
        message: str,
    ) -> None:
        output_path = self._recording_output
        self._recording_clock.stop()
        self._recording_job = None
        self._recording_output = None
        self._set_recording_controls(False)

        if success:
            self.status_label.setText(
                f"Recording saved: {output_path}"
            )
            QMessageBox.information(
                self,
                "Recording completed",
                f"Recording saved to:\n{output_path}",
            )
        else:
            self.status_label.setText(message.splitlines()[0])
            QMessageBox.critical(
                self,
                "Recording failed",
                message,
            )

    def _set_recording_controls(self, recording: bool) -> None:
        self.start_button.setEnabled(not recording)
        self.stop_button.setEnabled(recording)
        self.refresh_backend_button.setEnabled(not recording)
        self.monitor_combo.setEnabled(not recording)
        self.refresh_monitors_button.setEnabled(not recording)
        self.mode_combo.setEnabled(not recording)
        self.width_spin.setEnabled(not recording)
        self.height_spin.setEnabled(not recording)
        self.show_area_button.setEnabled(not recording)
        self.hide_area_button.setEnabled(not recording)
        self.output_picker.setEnabled(not recording)
        self.filename_edit.setEnabled(not recording)
        self.fps_combo.setEnabled(not recording)

    def _update_recording_clock(self) -> None:
        if not self._elapsed_timer.isValid():
            return
        total_seconds = self._elapsed_timer.elapsed() // 1000
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.recording_time_label.setText(
            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        )

    def is_recording(self) -> bool:
        return (
            self._recording_job is not None
            or self._pending_launch is not None
        )

    def stop_recording(self) -> None:
        self._stop_recording()
