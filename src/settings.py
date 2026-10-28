import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils.app_paths import settings_file_path


class AppSettings:
    INPUT_DIR_KEY = "paths/input_dir"
    EXPORT_DIR_KEY = "paths/export_dir"
    RECORD_DIR_KEY = "paths/record_dir"
    PROJECT_DIR_KEY = "paths/project_dir"

    def __init__(self) -> None:
        self._path = settings_file_path()
        self._values: Dict[str, Any] = {}
        self._load()

    def input_dir(self) -> str:
        return str(self.value(self.INPUT_DIR_KEY, str(Path.home())))

    def set_input_dir(self, path: str) -> None:
        self.set_value(self.INPUT_DIR_KEY, path)

    def export_dir(self) -> str:
        return str(self.value(self.EXPORT_DIR_KEY, str(Path.home())))

    def set_export_dir(self, path: str) -> None:
        self.set_value(self.EXPORT_DIR_KEY, path)

    def record_dir(self) -> str:
        return str(self.value(self.RECORD_DIR_KEY, str(Path.home())))

    def set_record_dir(self, path: str) -> None:
        self.set_value(self.RECORD_DIR_KEY, path)

    def project_dir(self) -> str:
        return str(self.value(self.PROJECT_DIR_KEY, str(Path.home())))

    def set_project_dir(self, path: str) -> None:
        self.set_value(self.PROJECT_DIR_KEY, path)

    def value(
        self,
        key: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        value = self._values.get(key, default)
        if value is None:
            return None
        return str(value)

    def set_value(self, key: str, value: str) -> None:
        self._values[str(key)] = str(value)
        self._save()

    def _load(self) -> None:
        try:
            if self._path.is_file():
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._values = raw
        except (OSError, json.JSONDecodeError):
            self._values = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._path.with_suffix(self._path.suffix + ".tmp")
        payload = json.dumps(
            self._values,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        temp.write_text(payload + "\n", encoding="utf-8")
        temp.replace(self._path)
