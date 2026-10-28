from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class CapturePreset:
    name: str
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    aspect_ratio: Optional[float] = None

    @property
    def is_fixed_size(self) -> bool:
        return self.width_px is not None and self.height_px is not None


PRESETS = (
    CapturePreset("1920 x 1080", width_px=1920, height_px=1080),
    CapturePreset("1280 x 720", width_px=1280, height_px=720),
    CapturePreset("1024 x 1024", width_px=1024, height_px=1024),
    CapturePreset("16:9 aspect ratio", aspect_ratio=16 / 9),
    CapturePreset("9:16 aspect ratio", aspect_ratio=9 / 16),
    CapturePreset("1:1 aspect ratio", aspect_ratio=1.0),
    CapturePreset("4:3 aspect ratio", aspect_ratio=4 / 3),
    CapturePreset("Custom"),
)


def preset_by_name(name: str) -> CapturePreset:
    for preset in PRESETS:
        if preset.name == name:
            return preset
    return PRESETS[-1]


def physical_size_to_logical(
    width_px: int,
    height_px: int,
    device_pixel_ratio: float,
) -> Tuple[int, int]:
    ratio = max(0.01, float(device_pixel_ratio))
    return (
        max(1, round(int(width_px) / ratio)),
        max(1, round(int(height_px) / ratio)),
    )


def logical_rect_to_physical(
    x: int,
    y: int,
    width: int,
    height: int,
    screen_x: int,
    screen_y: int,
    device_pixel_ratio: float,
) -> Tuple[int, int, int, int]:
    ratio = max(0.01, float(device_pixel_ratio))
    local_x = int(x) - int(screen_x)
    local_y = int(y) - int(screen_y)

    return (
        round(local_x * ratio),
        round(local_y * ratio),
        max(1, round(int(width) * ratio)),
        max(1, round(int(height) * ratio)),
    )


def clamp_rect_to_bounds(
    x: int,
    y: int,
    width: int,
    height: int,
    bounds_x: int,
    bounds_y: int,
    bounds_width: int,
    bounds_height: int,
) -> Tuple[int, int, int, int]:
    width = min(max(1, int(width)), max(1, int(bounds_width)))
    height = min(max(1, int(height)), max(1, int(bounds_height)))

    min_x = int(bounds_x)
    min_y = int(bounds_y)
    max_x = min_x + int(bounds_width) - width
    max_y = min_y + int(bounds_height) - height

    return (
        min(max(int(x), min_x), max_x),
        min(max(int(y), min_y), max_y),
        width,
        height,
    )


def fit_aspect_inside(
    requested_width: int,
    requested_height: int,
    aspect_ratio: float,
    max_width: int,
    max_height: int,
    min_size: int = 80,
) -> Tuple[int, int]:
    ratio = max(0.01, float(aspect_ratio))
    width = max(min_size, int(requested_width))
    height = max(min_size, int(requested_height))

    if width / max(1, height) >= ratio:
        height = round(width / ratio)
    else:
        width = round(height * ratio)

    if width > max_width:
        width = max_width
        height = round(width / ratio)

    if height > max_height:
        height = max_height
        width = round(height * ratio)

    return max(1, width), max(1, height)
