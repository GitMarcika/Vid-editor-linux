import unittest

from src.utils.timeline import build_clip_spans, locate_global_position, total_duration_ms


class TimelineTests(unittest.TestCase):
    def test_builds_cumulative_spans(self) -> None:
        spans = build_clip_spans([1000, 2500, 500])
        self.assertEqual(
            [(s.start_ms, s.end_ms) for s in spans],
            [(0, 1000), (1000, 3500), (3500, 4000)],
        )
        self.assertEqual(total_duration_ms(spans), 4000)

    def test_locates_global_position(self) -> None:
        spans = build_clip_spans([1000, 2500])
        span, local = locate_global_position(spans, 1750)
        self.assertEqual(span.index, 1)
        self.assertEqual(local, 750)

    def test_exact_end_maps_to_last_clip_end(self) -> None:
        spans = build_clip_spans([1000, 2500])
        span, local = locate_global_position(spans, 3500)
        self.assertEqual(span.index, 1)
        self.assertEqual(local, 2500)


if __name__ == "__main__":
    unittest.main()
