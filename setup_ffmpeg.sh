#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -x .venv/bin/python ]]; then
    PYTHON_BIN=".venv/bin/python"
else
    PYTHON_BIN=""
    for candidate in python3.9 python3.10 python3.11 python3; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if (3, 9) <= sys.version_info[:2] <= (3, 11) else 1)
PY
            then
                PYTHON_BIN="$(command -v "$candidate")"
                break
            fi
        fi
    done
fi

if [[ -z "$PYTHON_BIN" ]]; then
    echo "ERROR: A Python 3.9-3.11 runtime is required." >&2
    echo "Run ./install.sh first to create the local .venv." >&2
    exit 2
fi

exec "$PYTHON_BIN" tools/ffmpeg/install_ffmpeg.py "$@"
