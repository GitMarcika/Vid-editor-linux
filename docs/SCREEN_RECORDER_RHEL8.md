# Screen Recorder RHEL8 acceptance

Step 4 is complete only after the relevant backend passes on the real no-sudo RHEL8 workstation.

## Detect the session

Run:

```bash
./preflight.sh
echo "$XDG_SESSION_TYPE"
```

Then open **Help -> Diagnostics** in Vid Editor. The session/backend shown in both places should agree.

## Common GUI checks

1. Open the Screen Recorder tab.
2. Confirm connected monitors are listed.
3. Test 1920x1080, 1280x720, 1024x1024, 16:9, 9:16, 1:1, 4:3 and Custom.
4. Confirm the red capture region stays inside the selected monitor.
5. Confirm physical-pixel and Qt/logical geometry are displayed.
6. Test 30 FPS and 60 FPS.
7. Start recording and confirm the red region UI disappears before capture begins.
8. Confirm the elapsed timer runs.
9. Stop and confirm a valid MP4 is produced.
10. Confirm an existing destination is not destroyed if start/recording/finalization fails.

## X11 acceptance

Expected backend: **X11 / FFmpeg x11grab**.

1. Confirm preflight reports `x11grab: found`.
2. Position the floating red frame over a known region.
3. Record 10-20 seconds at 30 FPS.
4. Confirm the output contains exactly that region and the mouse pointer.
5. Repeat at 60 FPS.
6. If multiple monitors are present, test a secondary monitor.
7. If display scaling is not 100%, verify the physical capture boundaries against the red frame.
8. Stop a recording and immediately play the MP4 to confirm clean finalization.

## GNOME Wayland acceptance

Expected backend: **Wayland / GNOME Shell ScreencastArea**.

1. Confirm preflight reports `gdbus` and `ScreencastArea: found`.
2. Press **Show / position capture frame**.
3. Confirm Vid Editor presents a fullscreen transparent selection overlay on the selected monitor rather than trying to move a top-level window.
4. Move the red rectangle and resize an aspect-ratio preset.
5. Press Esc and confirm the overlay disappears.
6. Show it again, position it over a known region, then start recording.
7. Confirm the fullscreen selector disappears before GNOME begins capture.
8. Record 10-20 seconds and Stop.
9. Confirm the temporary GNOME WebM is converted to the requested MP4 and cleaned up.
10. Confirm the MP4 region corresponds to the selected rectangle.
11. Repeat on a secondary monitor if present.
12. If the monitor uses HiDPI scaling, verify the selected logical region and resulting physical video dimensions.
13. Confirm no system settings are changed and no sudo/root prompt occurs.

## Failure cases

- Wayland without GNOME Shell or without `ScreencastArea`: show a clear unsupported-backend error.
- X11 FFmpeg without `x11grab`: show a clear capability error.
- Missing FFmpeg: direct the user to `./setup_ffmpeg.sh`.
- Stop/finalization failure: do not overwrite an existing final MP4.
- Corporate policy blocking D-Bus screencast or execution: report the failure; do not attempt to bypass policy.

Do not install system packages with sudo as a workaround. Missing capabilities are inputs to Step 5 deployment/hardening.
