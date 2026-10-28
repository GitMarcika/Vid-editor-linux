#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${VIDEDITOR_BUILD_PYTHON:-python3.9}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "ERROR: $PYTHON_BIN is required on the BUILD machine." >&2
    exit 2
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info[:2] != (3, 9):
    raise SystemExit(
        f"Build must use Python 3.9 for the RHEL8 package; got {sys.version.split()[0]}"
    )
PY

echo "Build Python: $($PYTHON_BIN --version 2>&1)"
if [[ -r /etc/redhat-release ]]; then
    echo "Build OS: $(cat /etc/redhat-release)"
else
    echo "WARNING: /etc/redhat-release not found."
fi
if command -v ldd >/dev/null 2>&1; then
    echo "Build glibc: $(ldd --version 2>&1 | head -n1)"
fi

rm -rf .build-venv build dist
"$PYTHON_BIN" -m venv .build-venv

# shellcheck disable=SC1091
source .build-venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-build.txt

echo
echo "Preparing application-local FFmpeg runtime..."
python tools/ffmpeg/install_ffmpeg.py

echo
echo "Building PyInstaller one-folder package..."
python -m PyInstaller \
    --clean \
    --noconfirm \
    --onedir \
    --name VidEditor \
    --windowed \
    main.py

PACKAGE_DIR="dist/VidEditor"
mkdir -p "$PACKAGE_DIR/tools/ffmpeg"
cp tools/ffmpeg/ffmpeg "$PACKAGE_DIR/tools/ffmpeg/ffmpeg"
cp tools/ffmpeg/ffprobe "$PACKAGE_DIR/tools/ffmpeg/ffprobe"
chmod u+x "$PACKAGE_DIR/tools/ffmpeg/ffmpeg" "$PACKAGE_DIR/tools/ffmpeg/ffprobe"

cp packaging/run-portable.sh "$PACKAGE_DIR/run.sh"
cp packaging/portable-preflight.sh "$PACKAGE_DIR/preflight.sh"
chmod u+x "$PACKAGE_DIR/run.sh" "$PACKAGE_DIR/preflight.sh"
: > "$PACKAGE_DIR/portable.flag"

mkdir -p "$PACKAGE_DIR/user_data/logs"

ARCHIVE="dist/VidEditor-rhel8-x86_64.tar.gz"
tar -C dist -czf "$ARCHIVE" VidEditor
sha256sum "$ARCHIVE" > "$ARCHIVE.sha256"

echo
echo "Portable package ready:"
echo "  $PACKAGE_DIR/"
echo "  $ARCHIVE"
echo "  $ARCHIVE.sha256"
