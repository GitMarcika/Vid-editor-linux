import unittest

from src.utils.media_paths import media_reference_basename


class MediaPathTests(unittest.TestCase):
    def test_windows_absolute_path_on_linux(self) -> None:
        self.assertEqual(
            media_reference_basename(r"C:\videos\scene\clip.mp4"),
            "clip.mp4",
        )

    def test_windows_unc_path(self) -> None:
        self.assertEqual(
            media_reference_basename(r"\\server\share\clip.mp4"),
            "clip.mp4",
        )

    def test_posix_path(self) -> None:
        self.assertEqual(
            media_reference_basename("/mnt/media/clip.mp4"),
            "clip.mp4",
        )


if __name__ == "__main__":
    unittest.main()
