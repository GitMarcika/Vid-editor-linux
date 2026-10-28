from dataclasses import dataclass


@dataclass(frozen=True)
class RectF:
    x: float
    y: float
    width: float
    height: float


def fitted_rect(
    container_width: float,
    container_height: float,
    content_width: float,
    content_height: float,
) -> RectF:
    if (
        container_width <= 0
        or container_height <= 0
        or content_width <= 0
        or content_height <= 0
    ):
        return RectF(0.0, 0.0, 0.0, 0.0)

    scale = min(
        container_width / content_width,
        container_height / content_height,
    )
    width = content_width * scale
    height = content_height * scale
    return RectF(
        (container_width - width) / 2.0,
        (container_height - height) / 2.0,
        width,
        height,
    )


def clamp_crop_origin(
    x: int,
    y: int,
    crop_width: int,
    crop_height: int,
    video_width: int,
    video_height: int,
) -> tuple:
    max_x = max(0, video_width - crop_width)
    max_y = max(0, video_height - crop_height)
    return (
        min(max(0, int(x)), max_x),
        min(max(0, int(y)), max_y),
    )
