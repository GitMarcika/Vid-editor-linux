# Linux FFmpeg tools

Step 2 will place approved user-space Linux binaries here:

```text
tools/ffmpeg/ffmpeg
tools/ffmpeg/ffprobe
```

They must be executable (`chmod u+x`).

Lookup order on Linux:

1. application-local `tools/ffmpeg/ffmpeg` / `ffprobe`
2. binaries already available on the user's PATH

No sudo or system-wide FFmpeg installation is required by the application design.
