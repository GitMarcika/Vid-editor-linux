# Raw Cutter RHEL8 acceptance

Step 2 is complete only after these checks pass on the real no-sudo RHEL8 workstation.

## Bootstrap and FFmpeg

1. Run `./preflight.sh`.
2. Run `./install.sh`; verify no sudo/root prompt occurs.
3. Verify `tools/ffmpeg/ffmpeg` and `tools/ffmpeg/ffprobe` exist and are executable.
4. Run `./preflight.sh` again and confirm the local FFmpeg/FFprobe versions are reported.
5. If the corporate network blocks GitHub, repeat using an approved pre-downloaded archive:
   `VIDEDITOR_FFMPEG_ARCHIVE=/path/to/archive.tar.xz ./setup_ffmpeg.sh`.

## Raw Cutter

1. Start `./run.sh` and open a normal MP4/H.264 source.
2. Confirm source resolution and duration appear. These values are supplied by FFprobe even before Qt playback is trusted.
3. Confirm Play/Pause works and the timeline moves.
4. Seek to multiple positions.
5. Set Start and End from the playhead.
6. Choose an even crop size, drag the crop rectangle, and export.
7. Confirm the exported file opens and contains only the selected time/crop.
8. Cancel a second export and confirm no `.partial-...` file remains.
9. Export over an existing filename, then cancel/fail a render; confirm the previous final file is still intact.
10. Try an odd crop width or height and confirm the editor rejects it with the H.264/yuv420p compatibility message.
11. Test a source path and output path containing spaces and non-ASCII characters.

## Playback fallback

If Qt playback reports a codec/backend error but FFprobe metadata is visible, record the exact playback error. Crop/export can still be tested independently because media metadata and FFmpeg export do not depend on the Qt playback decoder.

Do not install system packages with sudo as a workaround. Missing desktop/runtime libraries are recorded for the later no-sudo deployment step.
