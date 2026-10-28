import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.settings import AppSettings


class SettingsTests(unittest.TestCase):
    def test_json_settings_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            with patch.dict(
                os.environ,
                {"VIDEDITOR_SETTINGS_FILE": str(path)},
                clear=False,
            ):
                first = AppSettings()
                first.set_input_dir("C:/input")
                first.set_export_dir("D:/export")

                second = AppSettings()
                self.assertEqual(second.input_dir(), "C:/input")
                self.assertEqual(second.export_dir(), "D:/export")
                self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
