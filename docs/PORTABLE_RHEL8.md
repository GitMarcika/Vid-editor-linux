# Portable RHEL8 deployment

This is the preferred target-machine deployment path.

## Goal

The RHEL8 workstation should not need:

- Python installation
- pip
- a virtualenv
- system FFmpeg/FFprobe
- sudo/root
- PATH changes
- writes to system directories

The portable package is a single extracted directory.

## Build artifact

The CI/build process produces:

```text
VidEditor-rhel8-x86_64.tar.gz
VidEditor-rhel8-x86_64.tar.gz.sha256
```

The build is performed with Python 3.9 inside Rocky Linux 8 and PyInstaller one-folder mode.

Linux PyInstaller applications still dynamically use the target system glibc, so the package is deliberately built on the RHEL8 generation rather than on a newer Ubuntu/Fedora host.

## Contents

After extraction:

```text
VidEditor/
  VidEditor
  _internal/
  run.sh
  preflight.sh
  portable.flag
  BUILD_INFO.txt
  THIRD_PARTY_NOTICES.md
  tools/
    ffmpeg/
      ffmpeg
      ffprobe
  user_data/
    logs/
```

`portable.flag` makes Vid Editor store settings and logs under `user_data/` in this directory.

## Target-machine install

Copy the tarball and checksum to a user-writable directory.

```bash
sha256sum -c VidEditor-rhel8-x86_64.tar.gz.sha256
tar -xzf VidEditor-rhel8-x86_64.tar.gz
cd VidEditor
./preflight.sh
./run.sh
```

No sudo command is part of this flow.

## Preflight

`preflight.sh` is read-only. It checks:

- x86_64 architecture
- executable presence
- bundled FFmpeg and FFprobe
- glibc / directly resolvable shared libraries
- key bundled Qt library dependencies
- X11 / Wayland session variables
- X11 x11grab capability when relevant
- gdbus presence for Wayland

A warning for an optional recorder capability does not prevent Raw Cutter or Assembly use.

## Build provenance

`BUILD_INFO.txt` records:

- source commit
- build Python
- PyInstaller version
- Rocky/RHEL build OS
- build glibc
- exact pinned FFmpeg asset/revision/SHA256

**Help -> Diagnostics** also displays this information.

## Reproducible FFmpeg

Portable builds pin:

```text
BtbN release: autobuild-2026-10-25-13-00
FFmpeg: n8.1.3-24-g92611900bb
asset: ffmpeg-n8.1.3-24-g92611900bb-linux64-gpl-8.1.tar.xz
SHA256: 3300aa8c1d68e79e20d22117d3748a6121a49fe09b7eece3dcc38b84a1104e71
```

The installer verifies the archive SHA256 before extracting it.

## Acceptance on the corporate machine

1. Extract under the user's home/work directory.
2. Run `./preflight.sh`; no root request should appear.
3. Run `./run.sh`; the GUI should start without any system Python dependency.
4. Open **Help -> Diagnostics** and verify `Frozen build: True` and the application-local FFmpeg paths.
5. Close and restart; settings should persist under `user_data/settings.json`.
6. Verify a log is created under `user_data/logs/`.
7. Run the Raw Cutter acceptance checklist.
8. Run the Assembly acceptance checklist.
9. Run the Screen Recorder checklist for the detected X11/Wayland backend.
10. Test paths containing spaces and non-ASCII characters.
11. Move the entire extracted `VidEditor` directory to another user-writable path and repeat startup/preflight to verify relocation.

If corporate application policy blocks the frozen executable, record the exact security/EDR message. Do not attempt to bypass application-control policy.
