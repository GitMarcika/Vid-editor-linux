#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export VIDEDITOR_PORTABLE=1
exec ./VidEditor "$@"
