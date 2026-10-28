# Assembly RHEL8 acceptance

Step 3 is complete only after these checks pass on the real no-sudo RHEL8 workstation.

## Runtime

1. Run `./preflight.sh`.
2. Confirm application-local FFmpeg and FFprobe are detected.
3. Confirm `libx264: found`.
4. Confirm `ASS/libass: found`.
5. Open **Help -> Diagnostics** and confirm the same FFmpeg capabilities are reported.

## Assembly timeline

1. Add at least three clips.
2. Include two different source resolutions and, if available, different FPS values.
3. Include at least one clip with audio and one clip without audio.
4. Confirm thumbnails, filenames and durations appear.
5. Drag/drop reorder the clips.
6. Confirm the global timeline duration updates and playback moves to the next clip.
7. Seek across clip boundaries and confirm the correct source/local position is selected.
8. Add the same source clip twice and confirm both instances remain independent.

## Text overlays

1. Add a text overlay by clicking the preview.
2. Move it and confirm its normalized position persists.
3. Set Start/End from the global playhead.
4. Change font, size, text color, background, outline and shadow.
5. Save and reopen the project and confirm all overlay data returns.
6. If a Windows-only font family is unavailable on Linux, note the fontconfig substitute; do not rewrite the stored project font name.

## Final export

1. Export to MP4.
2. Confirm output resolution is the first clip's resolution rounded to even dimensions if needed.
3. Confirm later clips preserve aspect ratio using black padding rather than stretching.
4. Confirm the final duration matches the Assembly global timeline.
5. Confirm clips without audio do not break audio continuity.
6. Confirm timed text appears at the expected position and interval.
7. Confirm background, outline and shadow are visible.
8. Start an export over an existing destination and cancel it; confirm the old final file remains unchanged and no partial file remains.
9. Test source/output paths containing spaces and non-ASCII characters.

## Windows project compatibility

1. Create or copy a Windows `.vedproj` whose stored media path resembles `C:\\videos\\clip.mp4`.
2. Put the referenced media file in the Linux project directory or a subdirectory.
3. Open the project on Linux.
4. Confirm Vid Editor resolves the source by basename without requiring the Windows absolute path.

Do not install system packages with sudo as a workaround. Record any missing runtime/font/display library for Step 5 hardening.
