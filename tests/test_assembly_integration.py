import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.services.assembly_export import build_assembly_export_arguments


@unittest.skipUnless(
    shutil.which("ffmpeg") and shutil.which("ffprobe"),
    "Assembly integration test requires ffmpeg and ffprobe.",
)
class AssemblyIntegrationTests(unittest.TestCase):
    def _run(self, args, timeout=40):
        completed = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stderr.decode("utf-8", errors="replace"),
        )
        return completed

    def test_mixed_clips_audio_and_ass_overlay_render(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        assert ffmpeg is not None
        assert ffprobe is not None

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.mp4"
            second = root / "second.mp4"
            output = root / "assembly.mp4"
            work = root / "work"

            self._run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=size=640x360:rate=30",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000",
                    "-t",
                    "1",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(first),
                ]
            )
            self._run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=320x240:rate=24",
                    "-t",
                    "1",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(second),
                ]
            )

            clips = [
                {"id": "a", "path": str(first), "duration_ms": 1000},
                {"id": "b", "path": str(second), "duration_ms": 1000},
            ]
            overlays = [
                {
                    "id": "txt",
                    "text": "Linux Assembly",
                    "start_ms": 250,
                    "end_ms": 1750,
                    "x_norm": 0.1,
                    "y_norm": 0.15,
                    "font_family": "DejaVu Sans",
                    "font_size": 28,
                    "text_color": "#ffffff",
                    "background_enabled": True,
                    "background_color": "#000000",
                    "background_opacity": 170,
                    "background_padding": 8,
                    "outline_enabled": True,
                    "outline_color": "#000000",
                    "outline_width": 2,
                    "shadow_enabled": True,
                    "shadow_color": "#000000",
                    "shadow_opacity": 160,
                    "shadow_blur": 8,
                    "shadow_offset_x": 3,
                    "shadow_offset_y": 3,
                }
            ]

            args, expected_ms, width, height, fps = (
                build_assembly_export_arguments(
                    clips,
                    overlays,
                    output,
                    work,
                )
            )
            self.assertEqual(expected_ms, 2000)
            self.assertEqual((width, height), (640, 360))
            self.assertAlmostEqual(fps, 30.0, places=2)
            self.assertTrue((work / "overlays.ass").is_file())

            self._run([ffmpeg] + args, timeout=60)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

            probed = self._run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "stream=codec_type,width,height:format=duration",
                    "-of",
                    "json",
                    str(output),
                ]
            )
            data = json.loads(probed.stdout.decode("utf-8"))
            types = [stream["codec_type"] for stream in data["streams"]]
            self.assertIn("video", types)
            self.assertIn("audio", types)

            video = next(
                stream
                for stream in data["streams"]
                if stream["codec_type"] == "video"
            )
            self.assertEqual((video["width"], video["height"]), (640, 360))

            duration = float(data["format"]["duration"])
            self.assertGreater(duration, 1.8)
            self.assertLess(duration, 2.2)


if __name__ == "__main__":
    unittest.main()
