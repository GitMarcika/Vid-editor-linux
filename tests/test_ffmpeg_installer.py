import importlib.util
import io
import tarfile
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "ffmpeg"
    / "install_ffmpeg.py"
)
SPEC = importlib.util.spec_from_file_location("ffmpeg_installer", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class FfmpegInstallerTests(unittest.TestCase):
    def test_default_build_targets_rhel8_compatible_linux_x64(self) -> None:
        self.assertIn("linux64-gpl-8.1.tar.xz", installer.DEFAULT_URL)

    def test_find_binary_prefers_bin_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            other = root / "other" / "ffmpeg"
            preferred = root / "package" / "bin" / "ffmpeg"
            other.parent.mkdir(parents=True)
            preferred.parent.mkdir(parents=True)
            other.write_text("other", encoding="utf-8")
            preferred.write_text("preferred", encoding="utf-8")
            self.assertEqual(
                installer.find_binary(root, "ffmpeg"),
                preferred,
            )

    def test_validate_features_requires_libx264_and_ass(self) -> None:
        responses = [
            SimpleNamespace(
                returncode=0,
                stdout=" V..... libx264 H.264 encoder\n",
            ),
            SimpleNamespace(
                returncode=0,
                stdout=" ... ass V->V Render ASS subtitles\n",
            ),
        ]
        with patch.object(
            installer.subprocess,
            "run",
            side_effect=responses,
        ):
            installer.validate_ffmpeg_features(Path("/fake/ffmpeg"))

    def test_validate_features_rejects_missing_ass(self) -> None:
        responses = [
            SimpleNamespace(
                returncode=0,
                stdout=" V..... libx264 H.264 encoder\n",
            ),
            SimpleNamespace(
                returncode=0,
                stdout=" ... scale V->V Scale video\n",
            ),
        ]
        with patch.object(
            installer.subprocess,
            "run",
            side_effect=responses,
        ):
            with self.assertRaises(RuntimeError):
                installer.validate_ffmpeg_features(Path("/fake/ffmpeg"))

    def test_safe_extract_rejects_parent_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "bad.tar.xz"
            payload = b"bad"

            with tarfile.open(archive, "w:xz") as tar:
                info = tarfile.TarInfo("../escape")
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))

            destination = root / "out"
            destination.mkdir()

            with self.assertRaises(RuntimeError):
                installer.safe_extract(archive, destination)


if __name__ == "__main__":
    unittest.main()
