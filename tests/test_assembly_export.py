import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.services.assembly_export import (
    build_ass_subtitles,
    build_assembly_export_arguments,
    build_filter_graph,
)
from src.services.media_info import VideoInfo


class AssemblyExportTests(unittest.TestCase):
    def test_ass_places_styles_before_events(self) -> None:
        text = build_ass_subtitles(
            [
                {
                    "id": "1",
                    "text": "Hello\nWorld",
                    "start_ms": 1000,
                    "end_ms": 2500,
                    "x_norm": 0.25,
                    "y_norm": 0.5,
                    "font_family": "Arial",
                    "font_size": 30,
                    "text_color": "#ff0000",
                    "background_enabled": True,
                    "background_color": "#000000",
                    "background_opacity": 128,
                    "background_padding": 10,
                    "outline_enabled": True,
                    "outline_color": "#ffffff",
                    "outline_width": 2,
                    "shadow_enabled": True,
                    "shadow_color": "#000000",
                    "shadow_opacity": 128,
                    "shadow_offset_x": 4,
                    "shadow_offset_y": 4,
                }
            ],
            1920,
            1080,
        )

        self.assertLess(text.index("Style: Text0"), text.index("[Events]"))
        self.assertLess(text.index("Style: Bg0"), text.index("[Events]"))
        self.assertIn(r"{\pos(480,540)}Hello\NWorld", text)

    def test_filter_graph_normalizes_and_concats(self) -> None:
        clips = [
            (
                Path("a.mp4"),
                1000,
                VideoInfo(1920, 1080, 30.0, True),
            ),
            (
                Path("b.mp4"),
                2000,
                VideoInfo(1280, 720, 60.0, False),
            ),
        ]
        graph = build_filter_graph(
            clips,
            1920,
            1080,
            30.0,
            Path("C:/tmp/overlays.ass"),
        )

        self.assertIn("scale=1920:1080", graph)
        self.assertIn("concat=n=2:v=1:a=1[vcat][acat]", graph)
        self.assertIn("anullsrc=channel_layout=stereo", graph)
        self.assertIn("[vcat]ass=", graph)

    def test_filter_graph_without_overlays_avoids_ass_filter(self) -> None:
        clips = [
            (
                Path("a.mp4"),
                1000,
                VideoInfo(1920, 1080, 30.0, False),
            ),
        ]
        graph = build_filter_graph(
            clips,
            1920,
            1080,
            30.0,
            None,
        )
        self.assertIn("[vcat]null[vout]", graph)
        self.assertNotIn("ass=", graph)

    def test_build_arguments_uses_first_clip_canvas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.mp4"
            second = root / "second.mp4"
            first.write_bytes(b"x")
            second.write_bytes(b"x")

            infos = {
                first: VideoInfo(1921, 1081, 29.97, True),
                second: VideoInfo(1280, 720, 60.0, False),
            }

            with patch(
                "src.services.assembly_export.probe_video_info",
                side_effect=lambda path: infos[path],
            ):
                args, total, width, height, fps = (
                    build_assembly_export_arguments(
                        [
                            {
                                "path": str(first),
                                "duration_ms": 1000,
                            },
                            {
                                "path": str(second),
                                "duration_ms": 2000,
                            },
                        ],
                        [],
                        root / "out.mp4",
                        root / "work",
                    )
                )

            self.assertEqual(total, 3000)
            self.assertEqual((width, height), (1920, 1080))
            self.assertAlmostEqual(fps, 29.97, places=2)
            self.assertIn("-filter_complex_script", args)
            self.assertIn("[vout]", args)
            self.assertIn("[acat]", args)


if __name__ == "__main__":
    unittest.main()
