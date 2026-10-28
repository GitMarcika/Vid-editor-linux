import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from src.gui.main_window import MainWindow
from src.gui.theme import DARK_STYLESHEET
from src.services.acceptance_probe import run_internal_acceptance
from src.services.diagnostics import build_diagnostics_report
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

    acceptance_file = os.environ.get(
        "VIDEDITOR_ACCEPTANCE_PROBE_FILE",
        "",
    ).strip()
    noninteractive = (
        os.environ.get("VIDEDITOR_SMOKE_TEST", "").strip() == "1"
        or bool(acceptance_file)
    )

    def show_uncaught_exception(message: str) -> None:
        if noninteractive:
            logger.critical(
                "Non-interactive run aborted by uncaught exception: %s",
                message,
            )
            app.exit(31)
            return

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

    if acceptance_file:
        try:
            accepted, probe_report = run_internal_acceptance(window)
            diagnostics = build_diagnostics_report()
            target = Path(acceptance_file).expanduser()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                probe_report
                + "\n"
                + diagnostics
                + "\n",
                encoding="utf-8",
            )
            logger.info(
                "Acceptance probe completed: %s (%s)",
                "PASS" if accepted else "FAIL",
                target,
            )
            exit_code = 0 if accepted else 32
        except Exception:
            logger.exception("Acceptance probe crashed")
            exit_code = 33
        QTimer.singleShot(50, lambda code=exit_code: app.exit(code))
    elif os.environ.get("VIDEDITOR_SMOKE_TEST", "").strip() == "1":
        QTimer.singleShot(750, app.quit)

    exit_code = app.exec()
    logger.info("Vid Editor exited with code %s", exit_code)
    return exit_code
