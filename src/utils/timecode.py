import re


_TIMECODE_RE = re.compile(
    r"^(?:(?P<hours>\d+):)?(?P<minutes>\d{1,2}):(?P<seconds>\d{2})(?:[\.,](?P<millis>\d{1,3}))?$"
)


def format_timecode(milliseconds: int) -> str:
    milliseconds = max(0, int(milliseconds))
    total_seconds, millis = divmod(milliseconds, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


def parse_timecode(value: str) -> int:
    text = value.strip()
    match = _TIMECODE_RE.fullmatch(text)
    if match is None:
        raise ValueError("Expected MM:SS.mmm or HH:MM:SS.mmm")

    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    millis_text = match.group("millis") or "0"

    if minutes > 59 and match.group("hours") is not None:
        raise ValueError("Minutes must be between 0 and 59")
    if seconds > 59:
        raise ValueError("Seconds must be between 0 and 59")

    millis = int(millis_text.ljust(3, "0"))
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis
