# RHEL8 / no-sudo baseline

## Target

- Red Hat Enterprise Linux 8 compatible workstation
- x86_64
- graphical desktop session
- no sudo/root requirement
- no writes to `/usr`, `/opt`, `/etc` or other system locations
- application state remains in user-writable locations

## Step 1 runtime assumption

Step 1 deliberately uses an already available Python 3.9, 3.10 or 3.11 to validate the application core quickly.

The bootstrap does **not** install Python system-wide and never attempts sudo. If a compatible Python or required system GUI libraries are absent, it stops with a diagnostic message. Step 5 provides the final user-space deployment path.

## Qt / display

PySide6 is installed only into the repository-local `.venv`.

The GUI requires an existing graphical desktop session. The current Qt imports require desktop libraries including `libEGL.so.1`; multimedia imports also require `libpulse.so.0`. A normal graphical RHEL8 workstation will often already provide these, but we verify rather than assume.

`preflight.sh` checks the system read-only, including Python, glibc, display/session variables and key shared libraries. It never invokes sudo.

X11 vs Wayland matters primarily for screen recording and is intentionally deferred until step 4.

Useful read-only checks on the real workstation:

```bash
./preflight.sh
cat /etc/redhat-release
uname -m
python3 --version
echo "$XDG_SESSION_TYPE"
echo "$DISPLAY"
echo "$WAYLAND_DISPLAY"
ldd --version | head -n1
```

## Source provenance

```text
GitMarcika/Vid-editor
branch: feature/video-editor-v1
commit: be9312f813741e23beae2788adc085592cff0aaa
```

Windows-only recorder code is not part of the Linux baseline.


## Screen recording baseline

RHEL8 GNOME can run on X11 or Wayland. The application detects the active session through `XDG_SESSION_TYPE`, `DISPLAY`, and `WAYLAND_DISPLAY`.

X11 requirements:

- application-local FFmpeg with the `x11grab` input device
- active `DISPLAY`

Wayland requirements:

- GNOME Shell session
- `gdbus` available in the user environment
- `org.gnome.Shell.Screencast.ScreencastArea` available on the session D-Bus
- application-local FFmpeg for final WebM -> MP4 conversion

The Wayland implementation does not use KMS/DRM capture and does not require DRM master, CAP_SYS_ADMIN, root, or sudo.


## Portable target baseline

The final no-sudo target path is the frozen one-folder package, not the source bootstrap.

Target requirements intentionally kept outside the package:

- x86_64 Linux kernel/userspace compatible with RHEL8
- glibc 2.28 or newer
- a graphical desktop session
- normal desktop X11/Wayland libraries provided by the workstation
- GNOME session D-Bus + gdbus only when using the GNOME Wayland recorder backend

Target requirements included in the package:

- Python interpreter/runtime
- PySide6 / Qt application runtime
- Vid Editor code
- FFmpeg and FFprobe
- launch/preflight scripts
- application-local settings/log directory

The package never writes to /usr, /opt, /etc, or another system directory.
