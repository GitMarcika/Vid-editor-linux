#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export VIDEDITOR_PORTABLE=1

RUNTIME_ROOT="$PWD/user_data/runtime"
mkdir -p     "$RUNTIME_ROOT/cache"     "$RUNTIME_ROOT/config"     "$RUNTIME_ROOT/data"     "$RUNTIME_ROOT/state"     "$RUNTIME_ROOT/tmp"     "$RUNTIME_ROOT/cache/mesa"

# Keep application/library caches and temp files inside the portable tree.
# Do not override XDG_RUNTIME_DIR: Wayland and the user-session D-Bus rely on it.
export XDG_CACHE_HOME="$RUNTIME_ROOT/cache"
export XDG_CONFIG_HOME="$RUNTIME_ROOT/config"
export XDG_DATA_HOME="$RUNTIME_ROOT/data"
export XDG_STATE_HOME="$RUNTIME_ROOT/state"
export TMPDIR="$RUNTIME_ROOT/tmp"
export MESA_SHADER_CACHE_DIR="$RUNTIME_ROOT/cache/mesa"

exec ./VidEditor "$@"
