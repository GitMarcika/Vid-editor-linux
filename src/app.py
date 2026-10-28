import logging
import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from src.gui.main_window import MainWindow
from src.gui.theme import DARK_STYLESHEET
from src.logging_setup import configure_logging, install_exception_hook


APP_ORGANIZATION = "GitMarcika"
APP_NAME = "VidEditor"


def run() -> int:
    log_path = configure_logging()
    logger = logging.getLogger(__name__)

    app = QApplication(sys.argv)
    app.setOrganizationName(APP_ORGANIZATION)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLESHEET)

    def show_uncaught_exception(message: str) -> None:
        QMessageBox.critical(
            None,
            "Unexpected error",
            "An unexpected error occurred.\n\n"
            f"{message}\n\n"
            f"Log file:\n{log_path}",
        )

    install_exception_hook(show_uncaught_exception)

    logger.info("Starting Vid Editor")
    window = MainWindow()
    window.show()

    if os.environ.get("VIDEDITOR_SMOKE_TEST", "").strip() == "1":
        QTimer.singleShot(750, app.quit)

    exit_code = app.exec()
    logger.info("Vid Editor exited with code %s", exit_code)
    return exit_code
