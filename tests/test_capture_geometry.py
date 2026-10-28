import unittest

from src.utils.capture_geometry import (
    clamp_rect_to_bounds,
    fit_aspect_inside,
    logical_rect_to_physical,
    physical_size_to_logical,
    preset_by_name,
)


class CaptureGeometryTests(unittest.TestCase):
    def test_fixed_preset(self) -> None:
        preset = preset_by_name("1920 x 1080")
        self.assertTrue(preset.is_fixed_size)
        self.assertEqual((preset.width_px, preset.height_px), (1920, 1080))

    def test_physical_size_to_logical_at_150_percent(self) -> None:
        self.assertEqual(
            physical_size_to_logical(1920, 1080, 1.5),
            (1280, 720),
        )

    def test_logical_rect_to_screen_relative_physical(self) -> None:
        self.assertEqual(
            logical_rect_to_physical(
                110,
                220,
                640,
                360,
                10,
                20,
                1.5,
            ),
            (150, 300, 960, 540),
        )

    def test_clamps_to_monitor(self) -> None:
        self.assertEqual(
            clamp_rect_to_bounds(900, 700, 400, 300, 0, 0, 1000, 800),
            (600, 500, 400, 300),
        )

    def test_fits_aspect_inside_monitor(self) -> None:
        width, height = fit_aspect_inside(1000, 800, 16 / 9, 1200, 700)
        self.assertLessEqual(width, 1200)
        self.assertLessEqual(height, 700)
        self.assertAlmostEqual(width / height, 16 / 9, places=2)


if __name__ == "__main__":
    unittest.main()
