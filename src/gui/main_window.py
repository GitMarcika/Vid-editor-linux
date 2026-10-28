from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTabWidget,
)

from src.gui.dialogs.diagnostics_dialog import DiagnosticsDialog
from src.gui.tabs.assembly_tab import AssemblyTab
from src.gui.tabs.raw_cutter_tab import RawCutterTab
from src.gui.tabs.recorder_tab import RecorderTab
from src.project import empty_project, load_project, save_project
from src.settings import AppSettings
from src.utils.media_paths import media_reference_basename


PROJECT_FILTER = "Vid Editor Project (*.vedproj);;JSON files (*.json);;All files (*.*)"
MEDIA_FILTER = (
    "Video files (*.mp4 *.mov *.mkv *.avi *.m4v *.webm *.wmv);;"
    "All files (*.*)"
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = AppSettings()
        self._project_path: Optional[Path] = None
        self._modified = False

        self.resize(1280, 800)
        self.setMinimumSize(960, 640)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.raw_tab = RawCutterTab(self.settings)
        self.assembly_tab = AssemblyTab(self.settings)
        self.recorder_tab = RecorderTab(self.settings)

        self.tabs.addTab(self.raw_tab, "Raw Cutter")
        self.tabs.addTab(self.assembly_tab, "Assembly")
        self.tabs.addTab(self.recorder_tab, "Screen Recorder")

        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage("Ready")

        self.setDockNestingEnabled(True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.raw_tab.projectChanged.connect(self._mark_modified)
        self.assembly_tab.projectChanged.connect(self._mark_modified)

        self._create_file_menu()
        self._create_help_menu()
        self._update_window_title()

    def _create_file_menu(self) -> None:
        menu = self.menuBar().addMenu("&File")

        new_action = QAction("&New Project", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._new_project)
        menu.addAction(new_action)

        open_action = QAction("&Open Project...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_project)
        menu.addAction(open_action)

        menu.addSeparator()

        save_action = QAction("&Save Project", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_project)
        menu.addAction(save_action)

        save_as_action = QAction("Save Project &As...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._save_project_as)
        menu.addAction(save_as_action)

        menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

    def _create_help_menu(self) -> None:
        menu = self.menuBar().addMenu("&Help")

        diagnostics_action = QAction("&Diagnostics...", self)
        diagnostics_action.triggered.connect(self._show_diagnostics)
        menu.addAction(diagnostics_action)

    def _show_diagnostics(self) -> None:
        dialog = DiagnosticsDialog(self)
        dialog.exec()

    def _new_project(self) -> None:
        if not self._ensure_no_active_operations():
            return
        if not self._maybe_save_changes():
            return

        self.raw_tab.clear_project()
        self.assembly_tab.clear_project()
        self._project_path = None
        self._set_modified(False)
        self.statusBar().showMessage("New project")

    def _open_project(self) -> None:
        if not self._ensure_no_active_operations():
            return
        if not self._maybe_save_changes():
            return

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Vid Editor project",
            self.settings.project_dir(),
            PROJECT_FILTER,
        )
        if not filename:
            return

        path = Path(filename)

        try:
            data = load_project(path)
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.critical(
                self,
                "Open project",
                f"Could not open the project:\n{exc}",
            )
            return

        resolved = deepcopy(data)
        if not self._resolve_project_media(resolved, path.parent):
            return

        try:
            self.raw_tab.load_project_state(resolved.get("raw_cutter", {}))
            self.assembly_tab.load_project_state(resolved.get("assembly", {}))
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.critical(
                self,
                "Open project",
                f"Could not restore the project:\n{exc}",
            )
            return

        self._project_path = path
        self.settings.set_project_dir(str(path.parent))
        self._set_modified(False)
        self.statusBar().showMessage(f"Project loaded: {path.name}")

    def _save_project(self) -> bool:
        if self._project_path is None:
            return self._save_project_as()

        data = self._collect_project_data()
        try:
            save_project(self._project_path, data)
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.critical(
                self,
                "Save project",
                f"Could not save the project:\n{exc}",
            )
            return False

        self.settings.set_project_dir(str(self._project_path.parent))
        self._set_modified(False)
        self.statusBar().showMessage(
            f"Project saved: {self._project_path.name}"
        )
        return True

    def _save_project_as(self) -> bool:
        start_path = self.settings.project_dir()
        if self._project_path is not None:
            start_path = str(self._project_path)

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Vid Editor project",
            start_path,
            PROJECT_FILTER,
        )
        if not filename:
            return False

        path = Path(filename)
        if path.suffix.lower() not in (".vedproj", ".json"):
            path = path.with_suffix(".vedproj")

        self._project_path = path
        return self._save_project()

    def _collect_project_data(self) -> Dict[str, Any]:
        data = empty_project()
        data["raw_cutter"] = self.raw_tab.project_state()
        data["assembly"] = self.assembly_tab.project_state()
        return data

    def _resolve_project_media(
        self,
        data: Dict[str, Any],
        project_dir: Path,
    ) -> bool:
        raw_state = data.get("raw_cutter", {})
        raw_reference = raw_state.get("source_video")
        if raw_reference:
            resolved = self._resolve_media_reference(
                str(raw_reference),
                project_dir,
            )
            if resolved is None:
                return False
            raw_state["source_video"] = str(resolved)

        assembly = data.get("assembly", {})
        clips = assembly.get("clips", [])
        for clip in clips:
            if not isinstance(clip, dict):
                continue
            reference = clip.get("path")
            if not reference:
                continue
            resolved = self._resolve_media_reference(
                str(reference),
                project_dir,
            )
            if resolved is None:
                return False
            clip["path"] = str(resolved)

        return True

    def _resolve_media_reference(
        self,
        reference: str,
        project_dir: Path,
    ) -> Optional[Path]:
        original = Path(reference)
        basename = media_reference_basename(reference)

        candidates = [original]
        if not original.is_absolute():
            candidates.append(project_dir / original)
        if basename:
            candidates.append(project_dir / basename)

        seen = set()
        for candidate in candidates:
            key = str(candidate)
            if key in seen:
                continue
            seen.add(key)
            if candidate.is_file():
                return candidate.resolve()

        try:
            matches = list(project_dir.rglob(basename)) if basename else []
        except OSError:
            matches = []
        for match in matches:
            if match.is_file():
                return match.resolve()

        answer = QMessageBox.question(
            self,
            "Missing video",
            "A video referenced by the project could not be found:\n\n"
            f"{reference}\n\nLocate it manually?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return None

        filename, _ = QFileDialog.getOpenFileName(
            self,
            f"Locate {basename or original.name}",
            str(project_dir),
            MEDIA_FILTER,
        )
        if not filename:
            return None
        return Path(filename).resolve()

    def _mark_modified(self) -> None:
        self._set_modified(True)

    def _set_modified(self, modified: bool) -> None:
        self._modified = bool(modified)
        self._update_window_title()

    def _update_window_title(self) -> None:
        if self._project_path is None:
            project_name = "Untitled"
        else:
            project_name = self._project_path.name

        marker = " *" if self._modified else ""
        self.setWindowTitle(f"Vid Editor - {project_name}{marker}")

    def _maybe_save_changes(self) -> bool:
        if not self._modified:
            return True

        answer = QMessageBox.question(
            self,
            "Unsaved project",
            "The project has unsaved changes. Save them now?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )

        if answer == QMessageBox.Cancel:
            return False
        if answer == QMessageBox.Save:
            return self._save_project()
        return True

    def _ensure_no_active_operations(self) -> bool:
        active = []
        if self.raw_tab.is_exporting():
            active.append("Raw Cutter export")
        if self.assembly_tab.is_exporting():
            active.append("Assembly export")
        if self.recorder_tab.is_recording():
            active.append("Screen recording")

        if not active:
            return True

        QMessageBox.warning(
            self,
            "Operation still running",
            "Stop or cancel the active operation before continuing:\n\n"
            + "\n".join(f"- {name}" for name in active),
        )
        return False

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._ensure_no_active_operations():
            event.ignore()
            return

        if self._maybe_save_changes():
            event.accept()
        else:
            event.ignore()
