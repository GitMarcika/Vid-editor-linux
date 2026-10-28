# Linux FFmpeg tools

Vid Editor uses application-local user-space binaries:

```text
tools/ffmpeg/ffmpeg
tools/ffmpeg/ffprobe
```

No sudo or system-wide FFmpeg installation is required.

## Automatic setup

From the repository root:

```bash
./setup_ffmpeg.sh
```

If the binaries already exist and pass the runtime/libx264 validation, the script is idempotent and does nothing.

The default online package is:

```text
BtbN FFmpeg-Builds
ffmpeg-n8.1-latest-linux64-gpl-8.1.tar.xz
```

This Linux build family targets RHEL/CentOS 8 (glibc 2.28 / Linux 4.18) and newer.

## Offline setup

Download/copy the compatible tar.xz archive through an approved route, then run:

```bash
VIDEDITOR_FFMPEG_ARCHIVE=/path/to/archive.tar.xz ./setup_ffmpeg.sh
```

Optional SHA256 verification:

```bash
VIDEDITOR_FFMPEG_ARCHIVE=/path/to/archive.tar.xz \
VIDEDITOR_FFMPEG_SHA256=<expected-sha256> \
./setup_ffmpeg.sh
```

The installer validates that both binaries start and that FFmpeg provides `libx264`.

Lookup order used by the application:

1. application-local `tools/ffmpeg/ffmpeg` / `ffprobe`
2. binaries already available on PATH
