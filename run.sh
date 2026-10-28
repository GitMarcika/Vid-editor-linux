#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
    echo "ERROR: .venv is missing. Run ./install.sh first." >&2
    exit 2
fi

# shellcheck disable=SC1091
source .venv/bin/activate
exec python main.py "$@"
