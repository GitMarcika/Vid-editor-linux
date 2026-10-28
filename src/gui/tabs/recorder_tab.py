from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.settings import AppSettings


class RecorderTab(QWidget):
    """Linux step-1 placeholder without Windows capture imports."""

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings

        root = QVBoxLayout(self)
        group = QGroupBox("Screen Recorder")
        layout = QVBoxLayout(group)

        title = QLabel("Linux recorder backend is not enabled yet.")
        title.setStyleSheet("font-weight:600;")
        layout.addWidget(title)

        details = QLabel(
            "This is intentional in port step 1. The editor GUI, projects "
            "and shared application core can run without importing the "
            "Windows gdigrab / WinAPI backend. X11 or Wayland capture will "
            "be selected and implemented in port step 4."
        )
        details.setWordWrap(True)
        details.setStyleSheet("color:#9aa0a6;")
        layout.addWidget(details)

        root.addWidget(group)
        root.addStretch(1)

    def is_recording(self) -> bool:
        return False

    def stop_recording(self) -> None:
        pass
