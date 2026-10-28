# Vid Editor RHEL8 manual acceptance

Automatic acceptance must report **PASS** before this checklist is used.

Record PASS/FAIL and any exact error text beside each item.

## 1. Startup and persistence

- [ ] GUI opens without terminal errors or root/sudo prompt.
- [ ] Three tabs are visible: Raw Cutter, Assembly, Screen Recorder.
- [ ] Help -> Diagnostics shows **Frozen build: True**.
- [ ] Close and restart; normal settings persist in `user_data/settings.json`.
- [ ] A path containing spaces and non-ASCII characters can be selected and used.

## 2. Raw Cutter

Use a normal MP4/H.264 test video.

- [ ] Video opens; resolution and duration are correct.
- [ ] Play/Pause works.
- [ ] Seeking works at several positions.
- [ ] Start/End from playhead work.
- [ ] Crop rectangle moves and stays inside the video.
- [ ] MP4 export completes and the result has the requested time/crop.
- [ ] Cancel removes the partial output.
- [ ] Cancelling/failing an overwrite leaves the old final file intact.

## 3. Assembly

Use at least three clips, including mixed resolution/FPS and one clip without audio.

- [ ] Clips add with thumbnails/durations.
- [ ] Drag/drop reorder works.
- [ ] Global timeline/clip transitions are correct.
- [ ] Seeking across clip boundaries selects the correct source position.
- [ ] A text overlay can be added and moved.
- [ ] Text start/end timing works.
- [ ] Font, color, background, outline and shadow visibly work.
- [ ] Project save/reopen restores clips and overlays.
- [ ] Final MP4 export completes.
- [ ] Later clips are padded without stretching.
- [ ] Final duration matches the timeline.
- [ ] Audio continuity survives a clip with no audio.
- [ ] Overlay timing/position is acceptably consistent with preview.
- [ ] Cancel/failed overwrite preserves the previous final file.

## 4. Windows -> Linux project compatibility

- [ ] Open a Windows-created `.vedproj`.
- [ ] A stored path such as `C:\\videos\\clip.mp4` relocates by basename when the file is beside/below the project.
- [ ] Save and reopen the Linux copy successfully.

## 5. Screen Recorder

First confirm Help -> Diagnostics reports the same backend as `$XDG_SESSION_TYPE`.

### If X11

- [ ] Diagnostics reports **X11 / FFmpeg x11grab** ready.
- [ ] Monitor list is correct.
- [ ] 1920x1080, 1280x720, 1024x1024 and aspect presets behave correctly.
- [ ] Red floating capture frame can be positioned.
- [ ] 30 FPS recording works.
- [ ] 60 FPS recording works.
- [ ] Mouse cursor appears in the result.
- [ ] Secondary monitor works if available.
- [ ] Scaled/HiDPI display region matches the red frame if applicable.
- [ ] Stop finalizes a playable MP4.

### If GNOME Wayland

- [ ] Diagnostics reports **Wayland / GNOME Shell ScreencastArea** ready.
- [ ] Fullscreen transparent selector opens on the selected monitor.
- [ ] Red rectangle can be moved/resized.
- [ ] Esc hides the selector.
- [ ] Selector disappears before recording starts.
- [ ] 30 FPS recording works.
- [ ] 60 FPS recording works.
- [ ] Temporary GNOME WebM is converted to MP4 and removed.
- [ ] Resulting region matches the selected rectangle.
- [ ] Secondary monitor works if available.
- [ ] HiDPI output size matches the displayed physical target size if applicable.

## 6. Relocation and final sign-off

- [ ] Close the app.
- [ ] Move the entire extracted `VidEditor` directory to another user-writable path.
- [ ] Run `./preflight.sh` there.
- [ ] Run `./acceptance.sh` there.
- [ ] Start `./run.sh` again.
- [ ] No absolute path from the previous installation location is required.

### Sign-off

- Automatic acceptance: PASS / FAIL
- Manual acceptance: PASS / FAIL
- Session: X11 / Wayland
- RHEL version:
- Date:
- Notes:
