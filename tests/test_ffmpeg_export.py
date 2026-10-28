import unittest
from pathlib import Path

from src.services.ffmpeg_export import build_export_arguments


class FfmpegExportArgumentsTests(unittest.TestCase):
    def test_builds_trim_and_crop_arguments(self) -> None:
        args = build_export_arguments(
            Path("C:/input/source.mp4"),
            Path("C:/output/clip.mp4"),
            1250,
            5250,
            (10, 20, 640, 480),
        )

        self.assertIn("1.250000", args)
        self.assertIn("4.000000", args)
        self.assertIn("crop=640:480:10:20", args)
        self.assertIn("0:a?", args)
        self.assertEqual(Path(args[-1]), Path("C:/output/clip.mp4"))

    def test_rejects_invalid_time_range(self) -> None:
        with self.assertRaises(ValueError):
            build_export_arguments(
                Path("a.mp4"),
                Path("b.mp4"),
                5000,
                5000,
                (0, 0, 100, 100),
            )


if __name__ == "__main__":
    unittest.main()
