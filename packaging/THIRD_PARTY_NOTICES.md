# Third-party notices

The portable Linux package includes third-party components.

## FFmpeg / FFprobe

The package bundles the GPL static x86_64 build produced by BtbN/FFmpeg-Builds:

- BtbN release: `autobuild-2026-10-25-13-00`
- FFmpeg revision: `n8.1.3-24-g92611900bb`
- asset: `ffmpeg-n8.1.3-24-g92611900bb-linux64-gpl-8.1.tar.xz`
- SHA256: `3300aa8c1d68e79e20d22117d3748a6121a49fe09b7eece3dcc38b84a1104e71`
- source/build project: https://github.com/BtbN/FFmpeg-Builds
- FFmpeg source project: https://ffmpeg.org/

This is a GPL build because Vid Editor requires libx264 support. Anyone redistributing the bundled FFmpeg binaries is responsible for complying with the applicable FFmpeg, x264, and other component licenses.

## PySide6 / Qt

The portable package contains PySide6 and Qt runtime files installed from the pinned Python dependency `PySide6==6.5.3`. Their licenses remain their respective upstream licenses.


## xcb-util-cursor

The portable Linux package includes `libxcb-cursor.so.0` from the RHEL8/EPEL xcb-util-cursor package so Qt 6.5's X11 platform plugin can run without installing that package on the target workstation.

The xcb-util libraries remain subject to their upstream licenses.
