import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.services.media_info import find_ffprobe, probe_video_info


class MediaInfoTests(unittest.TestCase):
    def test_probe_video_info_includes_duration(self) -> None:
        payload = {
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30000/1001",
                },
                {"codec_type": "audio"},
            ],
            "format": {"duration": "12.345"},
        }
        completed = SimpleNamespace(
            returncode=0,
            stdout=json.dumps(payload).encode("utf-8"),
            stderr=b"",
        )

        with patch(
            "src.services.media_info.find_ffprobe",
            return_value="/fake/ffprobe",
        ), patch(
            "src.services.media_info.subprocess.run",
            return_value=completed,
        ):
            info = probe_video_info(Path("video.mp4"))

        self.assertEqual((info.width, info.height), (1920, 1080))
        self.assertAlmostEqual(info.fps, 30000 / 1001, places=4)
        self.assertTrue(info.has_audio)
        self.assertEqual(info.duration_ms, 12345)

    def test_probe_video_info_timeout_is_a_runtime_error(self) -> None:
        with patch(
            "src.services.media_info.find_ffprobe",
            return_value="/fake/ffprobe",
        ), patch(
            "src.services.media_info.subprocess.run",
            side_effect=subprocess.TimeoutExpired(
                cmd=["/fake/ffprobe"],
                timeout=20,
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "FFprobe timed out while reading video.mp4",
            ):
                probe_video_info(Path("video.mp4"))

    @unittest.skipIf(os.name == "nt", "Linux executable bit behavior test")
    def test_find_ffprobe_prefers_application_local_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "tools" / "ffmpeg" / "ffprobe"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            binary.chmod(0o755)

            with patch(
                "src.services.media_info.application_base_dir",
                return_value=root,
            ):
                self.assertEqual(find_ffprobe(), str(binary))


if __name__ == "__main__":
    unittest.main()
