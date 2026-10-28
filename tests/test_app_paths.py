import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.utils.app_paths import settings_file_path, user_data_dir


class AppPathTests(unittest.TestCase):
    def test_local_appdata_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(
                os.environ,
                {"LOCALAPPDATA": tmp, "VIDEDITOR_PORTABLE": ""},
                clear=False,
            ):
                self.assertEqual(
                    user_data_dir(),
                    Path(tmp) / "VidEditor",
                )

    def test_settings_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "custom.json"
            with patch.dict(
                os.environ,
                {"VIDEDITOR_SETTINGS_FILE": str(target)},
                clear=False,
            ):
                self.assertEqual(settings_file_path(), target)


if __name__ == "__main__":
    unittest.main()
