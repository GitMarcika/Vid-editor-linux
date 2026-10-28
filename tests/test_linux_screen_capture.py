import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.services.linux_screen_capture import (
    build_wayland_transcode_arguments,
    build_x11grab_arguments,
    check_ffmpeg_x11grab,
    check_gnome_screencast_area,
    detect_linux_session,
    gnome_screencast_start_arguments,
    make_even_region,
    parse_gdbus_bool_result,
    parse_gdbus_start_result,
    qt_rect_to_x11_region,
)


class LinuxScreenCaptureTests(unittest.TestCase):
    def test_detects_wayland_before_xwayland_display(self) -> None:
        info = detect_linux_session(
            {
                "XDG_SESSION_TYPE": "wayland",
                "WAYLAND_DISPLAY": "wayland-0",
                "DISPLAY": ":0",
            }
        )
        self.assertEqual(info.kind, "wayland")
        self.assertEqual(info.display, ":0")

    def test_detects_x11(self) -> None:
        info = detect_linux_session(
            {
                "XDG_SESSION_TYPE": "x11",
                "DISPLAY": ":1",
            }
        )
        self.assertEqual(info.kind, "x11")

    def test_even_region(self) -> None:
        self.assertEqual(
            make_even_region(-1200, 20, 641, 481),
            (-1200, 20, 640, 480),
        )

    def test_qt_rect_to_x11_physical_region(self) -> None:
        self.assertEqual(
            qt_rect_to_x11_region(
                frame_x=2020,
                frame_y=100,
                frame_width=640,
                frame_height=360,
                screen_x=1920,
                screen_y=0,
                device_pixel_ratio=1.5,
            ),
            (3030, 150, 960, 540),
        )

    def test_x11grab_arguments(self) -> None:
        args = build_x11grab_arguments(
            Path("/tmp/out.mp4"),
            60,
            ":0.0",
            (10, 20, 1280, 720),
        )
        self.assertIn("x11grab", args)
        self.assertIn(":0.0+10,20", args)
        self.assertIn("1280x720", args)
        self.assertIn("60", args)
        self.assertEqual(args[-1], "/tmp/out.mp4")

    def test_gnome_start_arguments_include_region_and_fps(self) -> None:
        args = gnome_screencast_start_arguments(
            (10, 20, 800, 600),
            Path("/tmp/capture.webm"),
            30,
        )
        self.assertIn("ScreencastArea", " ".join(args))
        self.assertIn("/tmp/capture.webm", args)
        self.assertIn("'framerate': <30>", args[-1])

    def test_parse_gdbus_start_result(self) -> None:
        success, filename = parse_gdbus_start_result(
            "(true, '/tmp/test.webm')"
        )
        self.assertTrue(success)
        self.assertEqual(filename, "/tmp/test.webm")

    def test_parse_gdbus_bool_result(self) -> None:
        self.assertTrue(parse_gdbus_bool_result("(true,)"))
        self.assertFalse(parse_gdbus_bool_result("(false,)"))

    def test_wayland_transcode_arguments(self) -> None:
        args = build_wayland_transcode_arguments(
            Path("/tmp/source.webm"),
            Path("/tmp/final.mp4"),
            (1921, 1081),
        )
        self.assertIn("libx264", args)
        self.assertIn("yuv420p", args)
        self.assertIn("+faststart", args)
        self.assertIn("scale=1920:1080", args)
        self.assertEqual(args[-1], "/tmp/final.mp4")

    def test_x11_capability_parser(self) -> None:
        completed = SimpleNamespace(
            returncode=0,
            stdout=" D  x11grab         X11 screen capture, using XCB\n",
        )
        with patch(
            "src.services.linux_screen_capture.subprocess.run",
            return_value=completed,
        ):
            ok, _ = check_ffmpeg_x11grab("/fake/ffmpeg")
        self.assertTrue(ok)

    def test_gnome_capability_parser(self) -> None:
        completed = SimpleNamespace(
            returncode=0,
            stdout="method ScreencastArea(...)\n",
        )
        with patch(
            "src.services.linux_screen_capture.subprocess.run",
            return_value=completed,
        ):
            ok, _ = check_gnome_screencast_area("/usr/bin/gdbus")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
