import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

from src.utils.app_paths import application_base_dir, settings_file_path, user_data_dir


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

    def test_frozen_application_base_is_executable_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "VidEditor"
            with patch.object(sys, "frozen", True, create=True), patch.object(
                sys,
                "executable",
                str(executable),
            ):
                self.assertEqual(
                    application_base_dir(),
                    Path(tmp).resolve(),
                )

    def test_portable_env_uses_application_local_user_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "VidEditor"
            with patch.object(sys, "frozen", True, create=True), patch.object(
                sys,
                "executable",
                str(executable),
            ), patch.dict(
                os.environ,
                {"VIDEDITOR_PORTABLE": "1"},
                clear=False,
            ):
                self.assertEqual(
                    user_data_dir(),
                    Path(tmp).resolve() / "user_data",
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
