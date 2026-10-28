import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from src.services.linux_screen_capture import build_x11grab_arguments


@unittest.skipUnless(
    shutil.which("ffmpeg")
    and shutil.which("ffprobe")
    and os.environ.get("DISPLAY"),
    "X11 capture integration test requires ffmpeg, ffprobe and DISPLAY.",
)
class X11CaptureIntegrationTests(unittest.TestCase):
    def test_x11grab_records_video(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        assert ffmpeg is not None
        assert ffprobe is not None

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "x11.mp4"
            args = build_x11grab_arguments(
                output,
                30,
                os.environ["DISPLAY"],
                (0, 0, 640, 360),
            )

            process = subprocess.Popen(
                [ffmpeg] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            time.sleep(1.0)
            stdout, stderr = process.communicate(
                input=b"q\n",
                timeout=15,
            )

            self.assertEqual(
                process.returncode,
                0,
                stderr.decode("utf-8", errors="replace"),
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
                timeout=15,
            )
            self.assertEqual(
                probed.returncode,
                0,
                probed.stderr.decode("utf-8", errors="replace"),
            )

            data = json.loads(probed.stdout.decode("utf-8"))
            stream = data["streams"][0]
            self.assertEqual((stream["width"], stream["height"]), (640, 360))
            self.assertGreater(float(data["format"]["duration"]), 0.5)


if __name__ == "__main__":
    unittest.main()
