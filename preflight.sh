#!/usr/bin/env bash
set -u

echo "Vid Editor Linux - read-only RHEL8 preflight"
echo "============================================="

if [[ -r /etc/redhat-release ]]; then
    echo "Red Hat release: $(cat /etc/redhat-release)"
else
    echo "Red Hat release: NOT DETECTED"
fi

echo "Kernel/arch: $(uname -srm)"
echo "Session type: ${XDG_SESSION_TYPE:-unknown}"
echo "DISPLAY: ${DISPLAY:-not set}"
echo "WAYLAND_DISPLAY: ${WAYLAND_DISPLAY:-not set}"

if command -v ldd >/dev/null 2>&1; then
    echo "glibc: $(ldd --version 2>&1 | head -n1)"
else
    echo "glibc/ldd: not found in PATH"
fi

echo
echo "Qt desktop shared libraries:"
if command -v ldconfig >/dev/null 2>&1; then
    for lib in libEGL.so.1 libpulse.so.0 libX11.so.6; do
        if ldconfig -p 2>/dev/null | grep -Fq "$lib"; then
            echo "  $lib: found"
        else
            echo "  $lib: NOT FOUND"
        fi
    done
else
    echo "  ldconfig is not available for library discovery"
fi

echo
echo "Python candidates:"
found=0
for candidate in python3.9 python3.10 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        found=1
        printf '  %-10s ' "$candidate"
        "$candidate" --version 2>&1
    fi
done
if [[ "$found" -eq 0 ]]; then
    echo "  none found"
fi

echo
echo "Application-local media tools:"
if [[ -x tools/ffmpeg/ffmpeg ]]; then
    echo "  ffmpeg: tools/ffmpeg/ffmpeg"
    tools/ffmpeg/ffmpeg -version 2>/dev/null | head -n1 || true
    if tools/ffmpeg/ffmpeg -hide_banner -encoders 2>/dev/null | grep -Fq "libx264"; then
        echo "  libx264: found"
    else
        echo "  libx264: NOT FOUND"
    fi
    if tools/ffmpeg/ffmpeg -hide_banner -filters 2>/dev/null | awk '{print $2}' | grep -Fxq "ass"; then
        echo "  ASS/libass: found"
    else
        echo "  ASS/libass: NOT FOUND"
    fi
else
    echo "  ffmpeg: not installed locally"
fi
if [[ -x tools/ffmpeg/ffprobe ]]; then
    echo "  ffprobe: tools/ffmpeg/ffprobe"
    tools/ffmpeg/ffprobe -version 2>/dev/null | head -n1 || true
else
    echo "  ffprobe: not installed locally"
fi

echo
echo "System/PATH media tools:"
command -v ffmpeg 2>/dev/null || echo "  ffmpeg: not on PATH"
command -v ffprobe 2>/dev/null || echo "  ffprobe: not on PATH"


echo
echo "Screen recorder backend:"
session_type="${XDG_SESSION_TYPE:-}"
if [[ "$session_type" == "wayland" || -n "${WAYLAND_DISPLAY:-}" ]]; then
    echo "  selected: Wayland / GNOME Shell ScreencastArea"
    if command -v gdbus >/dev/null 2>&1; then
        echo "  gdbus: $(command -v gdbus)"
        if gdbus introspect --session \
            --dest org.gnome.Shell.Screencast \
            --object-path /org/gnome/Shell/Screencast \
            2>/dev/null | grep -Fq "ScreencastArea"; then
            echo "  ScreencastArea: found"
        else
            echo "  ScreencastArea: NOT FOUND / unavailable in this session"
        fi
    else
        echo "  gdbus: NOT FOUND"
    fi
elif [[ "$session_type" == "x11" || -n "${DISPLAY:-}" ]]; then
    echo "  selected: X11 / FFmpeg x11grab"
    if [[ -x tools/ffmpeg/ffmpeg ]]; then
        if tools/ffmpeg/ffmpeg -hide_banner -devices 2>/dev/null \
            | grep -Fq "x11grab"; then
            echo "  x11grab: found"
        else
            echo "  x11grab: NOT FOUND"
        fi
    elif command -v ffmpeg >/dev/null 2>&1; then
        if ffmpeg -hide_banner -devices 2>/dev/null | grep -Fq "x11grab"; then
            echo "  x11grab: found on PATH FFmpeg"
        else
            echo "  x11grab: NOT FOUND on PATH FFmpeg"
        fi
    else
        echo "  x11grab: FFmpeg not available"
    fi
else
    echo "  selected: none"
    echo "  No X11 or Wayland graphical session detected."
fi

echo
echo "Preflight is read-only. No files or system settings were changed."
