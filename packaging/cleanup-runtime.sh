#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

RUNTIME_ROOT="$PWD/user_data/runtime"

if [[ ! -e "$RUNTIME_ROOT" ]]; then
    echo "No portable runtime cache/temp directory exists."
    exit 0
fi

rm -rf -- "$RUNTIME_ROOT"
echo "Removed portable runtime cache/temp data:"
echo "  $RUNTIME_ROOT"
echo
echo "Settings, logs, projects and acceptance reports were not removed."
