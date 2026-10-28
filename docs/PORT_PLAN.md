# RHEL8 port plan

Priority order:

1. reliability / actually working on the target machine
2. implementation speed
3. cleanup and optimization only after validation

The port is split into six implementation steps.

## Step 1 - Linux baseline and shared application core

- import the platform-independent editor/project code from the Windows edition
- do not import the WinAPI/gdigrab recording backend
- provide a Linux recorder placeholder so the main GUI can start
- provide no-sudo `install.sh` and `run.sh`
- retain JSON settings and filesystem logging
- add Linux Python 3.9/3.10 CI smoke tests
- document the exact source snapshot

Acceptance: on a RHEL8-class graphical workstation with a compatible Python already available, `./install.sh` creates only a repository-local venv and `./run.sh` starts the three-tab GUI without sudo.

## Step 2 - FFmpeg/FFprobe and Raw Cutter

User-space FFmpeg/FFprobe, playback validation, trim/crop/export.

## Step 3 - Assembly, overlays and final export

Validate clip timeline, project compatibility, styled overlays and final render.

## Step 4 - Linux Screen Recorder

Detect X11 vs Wayland first. Implement the appropriate Linux capture backend instead of porting Windows capture code.

## Step 5 - No-sudo deployment

Provide the target-machine user-space runtime/package. No writes to system directories.

## Step 6 - RHEL8 acceptance and hardening

Run the complete acceptance checklist on the real corporate workstation and fix observed compatibility/reliability issues before declaring the port complete.
