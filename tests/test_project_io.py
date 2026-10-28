import tempfile
import unittest
from pathlib import Path

from src.project.io import load_project, save_project
from src.project.model import empty_project


class ProjectIoTests(unittest.TestCase):
    def test_project_round_trip(self) -> None:
        data = empty_project()
        data["raw_cutter"] = {
            "source_video": "C:/video/source.mp4",
            "trim_start_ms": 1250,
            "trim_end_ms": 5000,
            "crop": {"x": 10, "y": 20, "width": 640, "height": 480},
        }
        data["assembly"]["clips"].append({"path": "C:/video/clip.mp4"})
        data["assembly"]["text_overlays"].append(
            {"text": "Hello", "start_ms": 0, "end_ms": 1000}
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.vedproj"
            save_project(path, data)
            restored = load_project(path)

        self.assertEqual(restored, data)

    def test_rejects_wrong_format(self) -> None:
        data = empty_project()
        data["format"] = "other"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.vedproj"
            path.write_text('{"format":"other","version":1}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_project(path)


if __name__ == "__main__":
    unittest.main()
