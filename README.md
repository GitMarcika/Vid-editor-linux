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
port/rhel8-step1
```

## Step 1 status

The shared application/editor core is present. Windows recording code is deliberately excluded and the Screen Recorder tab uses a Linux placeholder until the Linux capture backend is implemented.

On a RHEL8-class graphical workstation that already has Python 3.9-3.11:

```bash
./install.sh
./run.sh
```

The bootstrap creates only `.venv` inside the repository and never invokes sudo.

Step 1 intentionally does not promise final offline/runtime packaging yet. If the target machine lacks a compatible Python or required desktop libraries, the script stops cleanly; the final user-space runtime is Step 5.

See:

- `docs/PORT_PLAN.md`
- `docs/RHEL8_BASELINE.md`
- `docs/PROJECT_FORMAT.md`
