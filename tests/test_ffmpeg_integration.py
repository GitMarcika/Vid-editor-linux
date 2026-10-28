import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.services.ffmpeg_export import build_export_arguments


@unittest.skipUnless(
    shutil.which("ffmpeg") and shutil.which("ffprobe"),
    "FFmpeg integration test requires ffmpeg and ffprobe on PATH.",
)
class FfmpegIntegrationTests(unittest.TestCase):
    def test_raw_cutter_trim_crop_command_runs_end_to_end(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        assert ffmpeg is not None
        assert ffprobe is not None

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            output = root / "crop.mp4"

            generated = subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=size=640x480:rate=30",
                    "-t",
                    "2",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            self.assertEqual(
                generated.returncode,
                0,
                generated.stderr.decode("utf-8", errors="replace"),
            )

            args = build_export_arguments(
                source,
                output,
                500,
                1500,
                (100, 100, 320, 240),
            )
            exported = subprocess.run(
                [ffmpeg] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            self.assertEqual(
                exported.returncode,
                0,
                exported.stderr.decode("utf-8", errors="replace"),
            )
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

            probed = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=width,height:format=duration",
                    "-of",
                    "json",
                    str(output),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
            self.assertEqual(
                probed.returncode,
                0,
                probed.stderr.decode("utf-8", errors="replace"),
            )
            data = json.loads(probed.stdout.decode("utf-8"))
            video = data["streams"][0]
            self.assertEqual(video["width"], 320)
            self.assertEqual(video["height"], 240)

            duration = float(data["format"]["duration"])
            self.assertGreater(duration, 0.8)
            self.assertLess(duration, 1.2)


if __name__ == "__main__":
    unittest.main()
