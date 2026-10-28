from copy import deepcopy
from typing import Any, Dict, Iterable, List
from uuid import uuid4


def normalize_text_overlay(
    raw: Dict[str, Any],
    total_duration_ms: int,
) -> Dict[str, Any]:
    total = max(0, int(total_duration_ms))
    start_ms = max(0, int(raw.get("start_ms", 0)))
    end_default = total if total > start_ms else start_ms + 1000
    end_ms = max(start_ms, int(raw.get("end_ms", end_default)))

    if total > 0:
        start_ms = min(start_ms, total)
        end_ms = min(max(start_ms, end_ms), total)

    return {
        "id": str(raw.get("id") or uuid4().hex),
        "text": str(raw.get("text", "Text")),
        "start_ms": start_ms,
        "end_ms": end_ms,
        "x_norm": min(1.0, max(0.0, float(raw.get("x_norm", 0.5)))),
        "y_norm": min(1.0, max(0.0, float(raw.get("y_norm", 0.5)))),
        "font_family": str(raw.get("font_family", "Arial")),
        "font_size": max(6, min(300, int(raw.get("font_size", 28)))),
        "text_color": str(raw.get("text_color", "#ffffff")),
        "background_enabled": bool(raw.get("background_enabled", False)),
        "background_color": str(raw.get("background_color", "#000000")),
        "background_opacity": max(
            0,
            min(255, int(raw.get("background_opacity", 170))),
        ),
        "background_padding": max(
            0,
            min(100, int(raw.get("background_padding", 8))),
        ),
        "outline_enabled": bool(raw.get("outline_enabled", False)),
        "outline_color": str(raw.get("outline_color", "#000000")),
        "outline_width": max(
            0,
            min(20, int(raw.get("outline_width", 2))),
        ),
        "shadow_enabled": bool(raw.get("shadow_enabled", False)),
        "shadow_color": str(raw.get("shadow_color", "#000000")),
        "shadow_opacity": max(
            0,
            min(255, int(raw.get("shadow_opacity", 160))),
        ),
        "shadow_blur": max(
            0,
            min(100, int(raw.get("shadow_blur", 8))),
        ),
        "shadow_offset_x": int(raw.get("shadow_offset_x", 3)),
        "shadow_offset_y": int(raw.get("shadow_offset_y", 3)),
    }


def sort_text_overlays(
    overlays: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    return sorted(
        (deepcopy(item) for item in overlays),
        key=lambda item: (
            int(item.get("start_ms", 0)),
            int(item.get("end_ms", 0)),
            str(item.get("id", "")),
        ),
    )


def is_text_overlay_active(
    overlay: Dict[str, Any],
    global_time_ms: int,
) -> bool:
    position = max(0, int(global_time_ms))
    start_ms = int(overlay.get("start_ms", 0))
    end_ms = int(overlay.get("end_ms", start_ms))
    return start_ms <= position <= end_ms
