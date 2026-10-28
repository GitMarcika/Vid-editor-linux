from typing import Callable, Optional

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget


class DirectoryPicker(QWidget):
    def __init__(
        self,
        label: str,
        initial_path: str = "",
        on_changed: Optional[Callable[[str], None]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._on_changed = on_changed

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(label)
        self.path_edit = QLineEdit(initial_path)
        self.browse_button = QPushButton("Browse...")

        layout.addWidget(self.label)
        layout.addWidget(self.path_edit, 1)
        layout.addWidget(self.browse_button)

        self.browse_button.clicked.connect(self._browse)
        self.path_edit.editingFinished.connect(self._emit_current)

    def path(self) -> str:
        return self.path_edit.text().strip()

    def set_path(self, path: str) -> None:
        self.path_edit.setText(path)
        self._notify(path)

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select folder",
            self.path() or "",
        )
        if selected:
            self.set_path(selected)

    def _emit_current(self) -> None:
        self._notify(self.path())

    def _notify(self, path: str) -> None:
        if self._on_changed is not None:
            self._on_changed(path)
