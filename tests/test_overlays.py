import unittest

from src.utils.overlays import (
    is_text_overlay_active,
    normalize_text_overlay,
    sort_text_overlays,
)


class OverlayTests(unittest.TestCase):
    def test_normalizes_position_and_times(self) -> None:
        overlay = normalize_text_overlay(
            {
                "text": "Hello",
                "start_ms": -10,
                "end_ms": 9000,
                "x_norm": 2.0,
                "y_norm": -1.0,
            },
            5000,
        )
        self.assertEqual(overlay["start_ms"], 0)
        self.assertEqual(overlay["end_ms"], 5000)
        self.assertEqual(overlay["x_norm"], 1.0)
        self.assertEqual(overlay["y_norm"], 0.0)
        self.assertEqual(overlay["font_family"], "Arial")
        self.assertEqual(overlay["font_size"], 28)
        self.assertEqual(overlay["text_color"], "#ffffff")
        self.assertFalse(overlay["background_enabled"])
        self.assertEqual(overlay["background_opacity"], 170)
        self.assertFalse(overlay["outline_enabled"])
        self.assertFalse(overlay["shadow_enabled"])

    def test_clamps_style_values(self) -> None:
        overlay = normalize_text_overlay(
            {
                "font_size": 999,
                "background_opacity": -5,
                "background_padding": 500,
                "outline_width": 99,
                "shadow_opacity": 999,
                "shadow_blur": 999,
            },
            5000,
        )
        self.assertEqual(overlay["font_size"], 300)
        self.assertEqual(overlay["background_opacity"], 0)
        self.assertEqual(overlay["background_padding"], 100)
        self.assertEqual(overlay["outline_width"], 20)
        self.assertEqual(overlay["shadow_opacity"], 255)
        self.assertEqual(overlay["shadow_blur"], 100)

    def test_sorts_by_start_time(self) -> None:
        overlays = [
            {"id": "b", "start_ms": 2000, "end_ms": 3000},
            {"id": "a", "start_ms": 1000, "end_ms": 2000},
        ]
        ordered = sort_text_overlays(overlays)
        self.assertEqual([item["id"] for item in ordered], ["a", "b"])

    def test_visibility_is_inclusive(self) -> None:
        overlay = {"start_ms": 1000, "end_ms": 2000}
        self.assertTrue(is_text_overlay_active(overlay, 1000))
        self.assertTrue(is_text_overlay_active(overlay, 1500))
        self.assertTrue(is_text_overlay_active(overlay, 2000))
        self.assertFalse(is_text_overlay_active(overlay, 999))
        self.assertFalse(is_text_overlay_active(overlay, 2001))


if __name__ == "__main__":
    unittest.main()
