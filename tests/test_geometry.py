import unittest

from src.utils.geometry import clamp_crop_origin, fitted_rect


class GeometryTests(unittest.TestCase):
    def test_fit_wide_video_into_square_container(self) -> None:
        rect = fitted_rect(1000, 1000, 1920, 1080)
        self.assertAlmostEqual(rect.x, 0.0)
        self.assertAlmostEqual(rect.width, 1000.0)
        self.assertAlmostEqual(rect.height, 562.5)
        self.assertAlmostEqual(rect.y, 218.75)

    def test_fit_tall_video_into_wide_container(self) -> None:
        rect = fitted_rect(1200, 600, 1080, 1920)
        self.assertAlmostEqual(rect.height, 600.0)
        self.assertAlmostEqual(rect.width, 337.5)
        self.assertAlmostEqual(rect.x, 431.25)
        self.assertAlmostEqual(rect.y, 0.0)

    def test_clamp_crop_origin(self) -> None:
        self.assertEqual(
            clamp_crop_origin(9999, -20, 640, 480, 1920, 1080),
            (1280, 0),
        )

    def test_crop_larger_than_video_clamps_to_zero(self) -> None:
        self.assertEqual(
            clamp_crop_origin(200, 100, 1920, 1080, 1280, 720),
            (0, 0),
        )


if __name__ == "__main__":
    unittest.main()
