#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -x .venv/bin/python ]]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "ERROR: Python is required to unpack the FFmpeg runtime." >&2
    exit 2
fi

exec "$PYTHON_BIN" tools/ffmpeg/install_ffmpeg.py "$@"
