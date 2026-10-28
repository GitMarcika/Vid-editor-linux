# RHEL8 port plan

Priority order:

1. reliability / actually working on the target machine
2. implementation speed
3. cleanup and optimization only after validation

The port is split into six implementation steps.

## Step 1 - Linux baseline and shared application core — IMPLEMENTED

- import the platform-independent editor/project code from the Windows edition
- do not import the WinAPI/gdigrab recording backend
- provide a Linux recorder placeholder so the main GUI can start
- provide no-sudo `install.sh` and `run.sh`
- retain JSON settings and filesystem logging
- add Linux Python 3.9/3.10 CI smoke tests
- document the exact source snapshot

Acceptance: on a RHEL8-class graphical workstation with a compatible Python already available, `./install.sh` creates only a repository-local venv and `./run.sh` starts the three-tab GUI without sudo.

## Step 2 - FFmpeg/FFprobe and Raw Cutter — IMPLEMENTED, awaiting RHEL8 validation

- RHEL8-compatible x86_64 static FFmpeg/FFprobe user-space provisioning
- online download or offline pre-downloaded archive path
- no sudo/system install
- local runtime preferred over PATH
- FFprobe duration and resolution fallback before Qt playback
- trim/crop H.264 export with yuv420p compatibility checks
- safe partial-file export; final file replaced only after successful render
- Linux FFmpeg end-to-end CI integration test

Acceptance is defined in `docs/RAW_CUTTER_RHEL8.md`.

## Step 3 - Assembly, overlays and final export — IMPLEMENTED, awaiting RHEL8 validation

- mixed-resolution/FPS clips normalized to the first clip canvas/FPS
- timeline duration explicitly applied to each video/audio segment
- silence inserted for clips without audio
- styled text overlays burned with ASS/libass
- application-local FFmpeg must provide libx264 + ASS
- safe partial-file final render and atomic replacement
- Windows-style media paths resolved correctly when opening .vedproj on Linux
- Linux end-to-end Assembly render test with audio/no-audio mixed clips and text overlay

Acceptance is defined in `docs/ASSEMBLY_RHEL8.md`.

## Step 4 - Linux Screen Recorder — IMPLEMENTED, awaiting RHEL8 validation

- automatic X11 vs Wayland session detection
- monitor-aware resolution/aspect presets and capture-area selection
- X11: direct FFmpeg x11grab recording
- Wayland/GNOME: org.gnome.Shell.Screencast.ScreencastArea over session D-Bus
- Wayland-safe fullscreen region-selection overlay instead of unsupported top-level window positioning
- capture frame hidden before recording starts
- 30/60 FPS
- graceful Stop
- Wayland WebM capture converted to final MP4 through application-local FFmpeg
- safe partial output / overwrite protection
- Help -> Diagnostics and preflight backend readiness checks
- real x11grab CI capture under Xvfb

Acceptance is defined in `docs/SCREEN_RECORDER_RHEL8.md`.

## Step 5 - No-sudo deployment — IMPLEMENTED, awaiting real RHEL8 validation

- PyInstaller one-folder package built with Python 3.9
- build runs inside Rocky Linux 8 to preserve the RHEL8/glibc 2.28 compatibility floor
- package contains Python runtime, PySide6/Qt application runtime and application code
- package contains pinned application-local FFmpeg/FFprobe
- no Python, pip, venv or FFmpeg installation required on the target machine
- no sudo/root requirement on the target machine
- portable.flag forces settings/logs into the package-local user_data directory
- package includes run.sh, read-only preflight.sh, BUILD_INFO.txt and third-party notices
- CI creates VidEditor-rhel8-x86_64.tar.gz plus SHA256 and smoke-starts the frozen GUI under Rocky 8/Xvfb

Acceptance is defined in `docs/PORTABLE_RHEL8.md`.

## Step 6 - RHEL8 acceptance and hardening

Run the complete acceptance checklist on the real corporate workstation and fix observed compatibility/reliability issues before declaring the port complete.
