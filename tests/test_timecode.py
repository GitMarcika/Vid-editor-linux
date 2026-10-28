import unittest

from src.utils.timecode import format_timecode, parse_timecode


class TimecodeTests(unittest.TestCase):
    def test_format_short_timecode(self) -> None:
        self.assertEqual(format_timecode(65_432), "01:05.432")

    def test_format_with_hours(self) -> None:
        self.assertEqual(format_timecode(3_661_007), "01:01:01.007")

    def test_parse_short_timecode(self) -> None:
        self.assertEqual(parse_timecode("01:05.432"), 65_432)

    def test_parse_hours(self) -> None:
        self.assertEqual(parse_timecode("01:01:01.007"), 3_661_007)

    def test_parse_comma_milliseconds(self) -> None:
        self.assertEqual(parse_timecode("00:02,5"), 2_500)

    def test_reject_invalid_seconds(self) -> None:
        with self.assertRaises(ValueError):
            parse_timecode("00:60.000")


if __name__ == "__main__":
    unittest.main()
