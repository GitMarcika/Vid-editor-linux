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
port/rhel8-step2
```

## Step 1 + Step 2 status

The shared application/editor core is present. Raw Cutter now has user-space FFmpeg/FFprobe provisioning and Linux-safe export hardening. Windows recording code remains deliberately excluded and the Screen Recorder tab uses a Linux placeholder until Step 4.

On a RHEL8-class graphical workstation that already has Python 3.9-3.11:

```bash
./preflight.sh
./install.sh
./run.sh
```

The bootstrap creates only `.venv` inside the repository and never invokes sudo.

Step 1 intentionally does not promise final offline/runtime packaging yet. If the target machine lacks a compatible Python or required desktop libraries, the script stops cleanly; the final user-space runtime is Step 5.

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
