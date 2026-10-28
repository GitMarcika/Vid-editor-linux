#!/usr/bin/env bash
set -u

cd "$(dirname "$0")"

STAMP="$(date +%Y%m%d-%H%M%S)"
RESULT_DIR="$PWD/user_data/acceptance/$STAMP"
mkdir -p "$RESULT_DIR"

SUMMARY="$RESULT_DIR/summary.txt"
SYSTEM_INFO="$RESULT_DIR/system-info.txt"
PREFLIGHT_LOG="$RESULT_DIR/preflight.txt"
APP_LOG="$RESULT_DIR/app-probe-console.txt"
PROBE_REPORT="$RESULT_DIR/internal-probe.txt"
SETTINGS_PROBE="$RESULT_DIR/acceptance-settings.json"

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

log() {
    printf '%s\n' "$*" | tee -a "$SUMMARY"
}

pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    log "[PASS] $*"
}

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    log "[FAIL] $*"
}

warn() {
    WARN_COUNT=$((WARN_COUNT + 1))
    log "[WARN] $*"
}

log "Vid Editor RHEL8 acceptance"
log "==========================="
log "Started: $(date --iso-8601=seconds 2>/dev/null || date)"
log "Package: $PWD"
log "Results: $RESULT_DIR"
log

{
    echo "uname=$(uname -a)"
    if [[ -r /etc/redhat-release ]]; then
        echo "redhat_release=$(cat /etc/redhat-release)"
    fi
    echo "uid=$(id -u)"
    echo "user=$(id -un 2>/dev/null || true)"
    echo "session=${XDG_SESSION_TYPE:-unknown}"
    echo "display=${DISPLAY:-not set}"
    echo "wayland_display=${WAYLAND_DISPLAY:-not set}"
    if command -v ldd >/dev/null 2>&1; then
        echo "glibc=$(ldd --version 2>&1 | head -n1)"
    fi
} > "$SYSTEM_INFO"

if [[ "$(uname -m)" == "x86_64" ]]; then
    pass "Architecture is x86_64."
else
    fail "Architecture is $(uname -m); package requires x86_64."
fi

if [[ "$(id -u)" -eq 0 ]]; then
    if [[ "${VIDEDITOR_ACCEPTANCE_ALLOW_ROOT:-0}" == "1" ]]; then
        warn "Acceptance is running as root because VIDEDITOR_ACCEPTANCE_ALLOW_ROOT=1."
    else
        warn "Acceptance is running as root; corporate target should be a normal user."
    fi
else
    pass "Running as a normal user; no sudo/root is required."
fi

if [[ -f ./portable.flag ]]; then
    pass "portable.flag is present."
else
    fail "portable.flag is missing."
fi

if [[ -x ./VidEditor && -x ./run.sh && -x ./preflight.sh ]]; then
    pass "Portable executable and launch scripts are executable."
else
    fail "One or more portable executables/scripts are missing."
fi

if [[ -x ./tools/ffmpeg/ffmpeg && -x ./tools/ffmpeg/ffprobe ]]; then
    pass "Bundled FFmpeg and FFprobe are executable."
else
    fail "Bundled FFmpeg/FFprobe are missing."
fi

WRITE_TEST="$PWD/user_data/.acceptance-write-$STAMP"
if mkdir -p "$PWD/user_data" 2>/dev/null && : > "$WRITE_TEST" 2>/dev/null; then
    rm -f "$WRITE_TEST"
    pass "Portable user_data directory is writable."
else
    fail "Portable user_data directory is not writable."
fi

if ./preflight.sh > "$PREFLIGHT_LOG" 2>&1; then
    pass "Portable preflight passed."
else
    code=$?
    fail "Portable preflight failed with exit code $code. See $PREFLIGHT_LOG"
fi

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
    fail "No graphical session is visible (DISPLAY/WAYLAND_DISPLAY missing)."
else
    pass "Graphical session variables are available."
fi

run_app_probe() {
    VIDEDITOR_PORTABLE=1 \
    VIDEDITOR_SETTINGS_FILE="$SETTINGS_PROBE" \
    VIDEDITOR_ACCEPTANCE_PROBE_FILE="$PROBE_REPORT" \
    ./run.sh > "$APP_LOG" 2>&1
}

if command -v timeout >/dev/null 2>&1; then
    timeout 180s bash -c '
        cd "$1"
        VIDEDITOR_PORTABLE=1 \
        VIDEDITOR_SETTINGS_FILE="$2" \
        VIDEDITOR_ACCEPTANCE_PROBE_FILE="$3" \
        ./run.sh
    ' _ "$PWD" "$SETTINGS_PROBE" "$PROBE_REPORT" > "$APP_LOG" 2>&1
    APP_CODE=$?
else
    run_app_probe
    APP_CODE=$?
fi

if [[ "$APP_CODE" -eq 0 ]]; then
    pass "Frozen application internal acceptance probe exited successfully."
else
    fail "Frozen application probe exited with code $APP_CODE. See $APP_LOG"
fi

if [[ -f "$PROBE_REPORT" ]]; then
    if grep -Fq "RESULT: PASS" "$PROBE_REPORT"; then
        pass "Internal application/service probe reports PASS."
    else
        fail "Internal application/service probe did not report PASS."
    fi
else
    fail "Internal application/service probe report was not created."
fi

if [[ -f ./user_data/logs/vid-editor.log ]]; then
    pass "Application log file exists under portable user_data."
    cp -f ./user_data/logs/vid-editor.log "$RESULT_DIR/vid-editor.log" 2>/dev/null || true
else
    fail "Application log file was not created."
fi

if [[ -f ./BUILD_INFO.txt ]]; then
    cp -f ./BUILD_INFO.txt "$RESULT_DIR/BUILD_INFO.txt"
    pass "Build provenance is available."
else
    fail "BUILD_INFO.txt is missing."
fi

if [[ -f ./ACCEPTANCE_MANUAL.md ]]; then
    cp -f ./ACCEPTANCE_MANUAL.md "$RESULT_DIR/ACCEPTANCE_MANUAL.md"
    pass "Manual GUI acceptance checklist is available."
else
    warn "ACCEPTANCE_MANUAL.md is missing."
fi

log
log "Automatic PASS: $PASS_COUNT"
log "Automatic FAIL: $FAIL_COUNT"
log "Warnings: $WARN_COUNT"

if [[ "$FAIL_COUNT" -eq 0 ]]; then
    log "AUTOMATIC RESULT: PASS"
    log
    log "Next: complete ACCEPTANCE_MANUAL.md for playback, editor interaction,"
    log "      overlays, and the active X11/Wayland recorder path."
    log "Report directory: $RESULT_DIR"
    exit 0
fi

log "AUTOMATIC RESULT: FAIL"
log "Report directory: $RESULT_DIR"
exit 1
