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
echo "Existing media tools:"
command -v ffmpeg 2>/dev/null || echo "  ffmpeg: not on PATH"
command -v ffprobe 2>/dev/null || echo "  ffprobe: not on PATH"

echo
echo "Preflight is read-only. No files or system settings were changed."
