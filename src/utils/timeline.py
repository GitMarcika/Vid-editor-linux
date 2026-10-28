from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class ClipSpan:
    index: int
    start_ms: int
    end_ms: int
    duration_ms: int


def build_clip_spans(durations_ms: Iterable[int]) -> List[ClipSpan]:
    spans: List[ClipSpan] = []
    cursor = 0

    for index, value in enumerate(durations_ms):
        duration = max(0, int(value))
        spans.append(
            ClipSpan(
                index=index,
                start_ms=cursor,
                end_ms=cursor + duration,
                duration_ms=duration,
            )
        )
        cursor += duration

    return spans


def total_duration_ms(spans: Iterable[ClipSpan]) -> int:
    total = 0
    for span in spans:
        total = max(total, span.end_ms)
    return total


def locate_global_position(
    spans: List[ClipSpan],
    position_ms: int,
) -> Optional[Tuple[ClipSpan, int]]:
    if not spans:
        return None

    position = max(0, int(position_ms))
    total = total_duration_ms(spans)
    if total <= 0:
        return spans[0], 0

    if position >= total:
        last = spans[-1]
        return last, last.duration_ms

    for span in spans:
        if span.start_ms <= position < span.end_ms:
            return span, position - span.start_ms

    return spans[-1], spans[-1].duration_ms
