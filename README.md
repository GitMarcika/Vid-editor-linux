# Vid Editor Linux

Linux / RHEL8 port of Vid Editor, optimized first for reliability and then for porting speed.

## Target

- RHEL 8 compatible x86_64 workstation
- no sudo/root required
- user-space Python environment/runtime
- user-space FFmpeg/FFprobe
- same `.vedproj` project format as the Windows edition

Initial Windows source snapshot:

```text
GitMarcika/Vid-editor
feature/video-editor-v1
be9312f813741e23beae2788adc085592cff0aaa
```

Current development branch:

```text
port/rhel8-step6
```

## Step 1 + Step 2 + Step 3 + Step 4 + Step 5 + Step 6 status

The shared application/editor core, Raw Cutter, Assembly and Linux Screen Recorder are present. Step 5 adds a frozen RHEL8 portable package so the target workstation does not need Python, pip, a venv, or a system FFmpeg installation.

Source/development mode on a RHEL8-class graphical workstation with Python 3.9-3.11:

```bash
./preflight.sh
./install.sh
./run.sh
```

The bootstrap creates only `.venv` inside the repository and never invokes sudo.

Normal target-machine use should prefer the Step 5 portable package below. Source/development mode remains available for debugging.

See:

- `docs/PORT_PLAN.md`
- `docs/RHEL8_BASELINE.md`
- `docs/PROJECT_FORMAT.md`


## FFmpeg setup

`./install.sh` automatically prepares an application-local FFmpeg runtime under `tools/ffmpeg/`.

For offline/restricted networks:

```bash
VIDEDITOR_FFMPEG_ARCHIVE=/path/to/ffmpeg.tar.xz ./setup_ffmpeg.sh
```

The default online source is the BtbN GPL static Linux x86_64 FFmpeg 8.1 release branch, which targets RHEL/CentOS 8 and newer.

See `docs/RAW_CUTTER_RHEL8.md` for the Step 2 acceptance checklist.


## Assembly on Linux

Step 3 validates the common Assembly editor on Linux:

- ordered multi-clip timeline
- mixed source resolution/FPS normalization
- optional source audio with silence for clips that have none
- timed styled text overlays rendered through ASS/libass
- safe final export using a partial file before replacing the destination
- Windows `.vedproj` media references can be relocated by filename on Linux

See `docs/ASSEMBLY_RHEL8.md`.


## Linux Screen Recorder

The recorder selects its backend from the active graphical session:

- **X11:** FFmpeg `x11grab` records the selected region directly to MP4.
- **GNOME Wayland:** the application calls GNOME Shell `ScreencastArea` over the user session D-Bus, then converts the GNOME WebM result to MP4 with the application-local FFmpeg.

Wayland does not allow arbitrary application-controlled top-level window positioning, so region setup uses a fullscreen transparent selection overlay on the selected monitor. X11 keeps the lightweight movable red frame.

No root/sudo access is required.

See `docs/SCREEN_RECORDER_RHEL8.md`.


## Portable RHEL8 package

The target workstation does **not** need Python, pip, a virtualenv or a system FFmpeg install.

CI/build output:

```text
VidEditor-rhel8-x86_64.tar.gz
VidEditor-rhel8-x86_64.tar.gz.sha256
```

Target-machine flow:

```bash
sha256sum -c VidEditor-rhel8-x86_64.tar.gz.sha256
tar -xzf VidEditor-rhel8-x86_64.tar.gz
cd VidEditor
./preflight.sh
./run.sh
```

Everything writable stays under the extracted directory, primarily `user_data/`. No sudo/root command is used.

The package is built in a Rocky Linux 8 environment because PyInstaller Linux bundles still use the target system's glibc; building on the oldest supported Linux generation avoids creating a binary that requires a newer glibc.

See `docs/PORTABLE_RHEL8.md`.


## Final RHEL8 acceptance

After extracting the portable package, run:

```bash
cd VidEditor
./acceptance.sh
```

The automatic runner creates:

```text
user_data/acceptance/YYYYMMDD-HHMMSS/
  summary.txt
  system-info.txt
  preflight.txt
  app-probe-console.txt
  internal-probe.txt
  BUILD_INFO.txt
  vid-editor.log
  ACCEPTANCE_MANUAL.md
```

Automatic acceptance exercises the **frozen packaged application**, not the source tree. It validates portable paths, settings/project persistence, bundled media tools, Raw Cutter service export, thumbnail extraction, Assembly render with ASS overlay, and the detected recorder backend capability.

After automatic **PASS**, complete the packaged `ACCEPTANCE_MANUAL.md` for the few interactions that require human visual confirmation.

The Linux port is not marked fully complete until both automatic and manual acceptance pass on the actual corporate RHEL8 workstation.
