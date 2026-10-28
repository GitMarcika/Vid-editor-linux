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

The GUI requires an existing graphical desktop session. X11 vs Wayland matters primarily for screen recording and is intentionally deferred until step 4.

Useful read-only checks on the real workstation:

```bash
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
