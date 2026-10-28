import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

from src.utils.app_paths import log_dir


def configure_logging() -> Path:
    directory = log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "vid-editor.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if not any(
        isinstance(handler, RotatingFileHandler)
        for handler in root.handlers
    ):
        handler = RotatingFileHandler(
            path,
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )
        )
        root.addHandler(handler)

    logging.getLogger(__name__).info("Logging initialized: %s", path)
    return path


def install_exception_hook(
    on_exception: Callable[[str], None],
) -> None:
    logger = logging.getLogger("uncaught")

    def hook(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        on_exception(str(exc_value) or exc_type.__name__)

    sys.excepthook = hook
