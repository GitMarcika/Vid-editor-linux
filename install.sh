#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "============================================"
echo "Vid Editor Linux - RHEL8 no-sudo bootstrap"
echo "============================================"
echo

if [[ -r /etc/redhat-release ]]; then
    echo "System: $(cat /etc/redhat-release)"
else
    echo "System: $(uname -srm)"
    echo "WARNING: /etc/redhat-release was not found."
fi

choose_python() {
    local candidate
    for candidate in python3.9 python3.10 python3.11 python3; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if (3, 9) <= sys.version_info[:2] <= (3, 11) else 1)
PY
            then
                printf '%s' "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_BIN="$(choose_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
    echo "ERROR: Python 3.9, 3.10 or 3.11 was not found."
    echo "No sudo command was attempted."
    echo "Port step 5 will provide the final fallback user-space runtime path."
    exit 2
fi

echo "Python: $($PYTHON_BIN --version 2>&1)"

if [[ ! -d .venv ]]; then
    echo "Creating local virtual environment: .venv"
    if ! "$PYTHON_BIN" -m venv .venv; then
        echo
        echo "ERROR: Python exists but could not create a venv."
        echo "No system installation or sudo fallback will be attempted."
        exit 3
    fi
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python - <<'PY'
import PySide6
from PySide6.QtWidgets import QApplication
print("PySide6:", PySide6.__version__)
print("Qt import smoke test: OK")
PY

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
    echo "WARNING: no DISPLAY or WAYLAND_DISPLAY is visible in this shell."
    echo "The GUI needs an existing graphical desktop session."
fi

echo
echo "Bootstrap complete."
echo "Start with: ./run.sh"
