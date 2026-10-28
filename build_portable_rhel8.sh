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
cp packaging/THIRD_PARTY_NOTICES.md "$PACKAGE_DIR/THIRD_PARTY_NOTICES.md"
chmod u+x "$PACKAGE_DIR/run.sh" "$PACKAGE_DIR/preflight.sh"
: > "$PACKAGE_DIR/portable.flag"

mkdir -p "$PACKAGE_DIR/user_data/logs"

SOURCE_COMMIT="$(git rev-parse HEAD 2>/dev/null || printf unknown)"
PYINSTALLER_VERSION="$(python -m PyInstaller --version 2>/dev/null || printf unknown)"
FFMPEG_VERSION="$(tools/ffmpeg/ffmpeg -version 2>/dev/null | head -n1 || true)"
{
    echo "package=VidEditor-rhel8-x86_64"
    echo "source_commit=$SOURCE_COMMIT"
    echo "build_python=$(python --version 2>&1)"
    echo "pyinstaller=$PYINSTALLER_VERSION"
    echo "ffmpeg_asset=ffmpeg-n8.1.3-24-g92611900bb-linux64-gpl-8.1.tar.xz"
    echo "ffmpeg_asset_sha256=3300aa8c1d68e79e20d22117d3748a6121a49fe09b7eece3dcc38b84a1104e71"
    echo "ffmpeg_version=$FFMPEG_VERSION"
    if [[ -r /etc/redhat-release ]]; then
        echo "build_os=$(cat /etc/redhat-release)"
    fi
    if command -v ldd >/dev/null 2>&1; then
        echo "build_glibc=$(ldd --version 2>&1 | head -n1)"
    fi
} > "$PACKAGE_DIR/BUILD_INFO.txt"

ARCHIVE_NAME="VidEditor-rhel8-x86_64.tar.gz"
ARCHIVE="dist/$ARCHIVE_NAME"
tar -C dist -czf "$ARCHIVE" VidEditor
(
    cd dist
    sha256sum "$ARCHIVE_NAME" > "$ARCHIVE_NAME.sha256"
)

echo
echo "Portable package ready:"
echo "  $PACKAGE_DIR/"
echo "  $ARCHIVE"
echo "  $ARCHIVE.sha256"
