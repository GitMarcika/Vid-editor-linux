#!/usr/bin/env bash
set -u

cd "$(dirname "$0")"

echo "Vid Editor portable RHEL8 preflight"
echo "=================================="
echo "Directory: $PWD"
echo "Kernel/arch: $(uname -srm)"
echo "Session: ${XDG_SESSION_TYPE:-unknown}"
echo "DISPLAY: ${DISPLAY:-not set}"
echo "WAYLAND_DISPLAY: ${WAYLAND_DISPLAY:-not set}"
echo "Portable runtime sandbox: $PWD/user_data/runtime"
echo "XDG_RUNTIME_DIR remains unchanged for Wayland/session D-Bus."

if [[ "$(uname -m)" != "x86_64" ]]; then
    echo "ERROR: this package targets x86_64."
    exit 2
fi

if [[ -x ./VidEditor ]]; then
    echo "VidEditor executable: found"
else
    echo "ERROR: VidEditor executable is missing/not executable."
    exit 3
fi

if [[ -x ./tools/ffmpeg/ffmpeg && -x ./tools/ffmpeg/ffprobe ]]; then
    echo "FFmpeg runtime: found"
    ./tools/ffmpeg/ffmpeg -version 2>/dev/null | head -n1 || true
    ./tools/ffmpeg/ffprobe -version 2>/dev/null | head -n1 || true
else
    echo "ERROR: bundled FFmpeg/FFprobe runtime is missing."
    exit 4
fi

if command -v ldd >/dev/null 2>&1; then
    echo "glibc: $(ldd --version 2>&1 | head -n1)"
    missing="$(ldd ./VidEditor 2>/dev/null | grep 'not found' || true)"
    if [[ -n "$missing" ]]; then
        echo "ERROR: executable has unresolved shared libraries:"
        echo "$missing"
        exit 5
    fi

    while IFS= read -r lib; do
        [[ -z "$lib" ]] && continue
        missing="$(ldd "$lib" 2>/dev/null | grep 'not found' || true)"
        if [[ -n "$missing" ]]; then
            echo "ERROR: unresolved libraries for $lib:"
            echo "$missing"
            exit 6
        fi
    done < <(
        find ./_internal -type f \( \
            -name 'libQt6Gui.so*' -o \
            -name 'libQt6Widgets.so*' -o \
            -name 'libQt6Multimedia.so*' \
        \) 2>/dev/null | head -n 10
    )

    if [[ "${XDG_SESSION_TYPE:-}" == "wayland" || -n "${WAYLAND_DISPLAY:-}" ]]; then
        platform_plugin="$(find . -type f \
            \( -name 'libqwayland-generic.so' -o -name 'libqwayland-egl.so' \) \
            2>/dev/null | head -n1)"
    else
        platform_plugin="$(find . -type f -name 'libqxcb.so' \
            2>/dev/null | head -n1)"
    fi

    if [[ -n "$platform_plugin" ]]; then
        missing="$(ldd "$platform_plugin" 2>/dev/null | grep 'not found' || true)"
        if [[ -n "$missing" ]]; then
            echo "ERROR: unresolved Qt platform-plugin libraries:"
            echo "$platform_plugin"
            echo "$missing"
            exit 7
        fi
        echo "Qt platform plugin dependencies: resolved"
    else
        echo "WARNING: matching Qt platform plugin was not found in _internal."
    fi
fi

if [[ "${XDG_SESSION_TYPE:-}" == "wayland" || -n "${WAYLAND_DISPLAY:-}" ]]; then
    if command -v gdbus >/dev/null 2>&1; then
        echo "Wayland gdbus: $(command -v gdbus)"
    else
        echo "WARNING: Wayland detected but gdbus is not available."
    fi
elif [[ "${XDG_SESSION_TYPE:-}" == "x11" || -n "${DISPLAY:-}" ]]; then
    if [[ -x ./tools/ffmpeg/ffmpeg ]]; then
        echo "X11 recorder: bundled FFmpeg executable found"
        echo "X11 x11grab: validated when recording actually starts"
    else
        echo "WARNING: bundled FFmpeg executable is unavailable."
    fi
fi

echo
echo "Portable preflight completed. No system files were changed."
