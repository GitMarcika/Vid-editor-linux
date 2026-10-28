#!/usr/bin/env python3
import argparse
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path


DEFAULT_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-n8.1-latest-linux64-gpl-8.1.tar.xz"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r:xz") as tar:
        root = destination.resolve()
        for member in tar.getmembers():
            target = (destination / member.name).resolve()
            if root != target and root not in target.parents:
                raise RuntimeError(
                    f"Unsafe path in FFmpeg archive: {member.name}"
                )
        tar.extractall(destination)


def find_binary(root: Path, name: str) -> Path:
    candidates = [
        path
        for path in root.rglob(name)
        if path.is_file() and path.parent.name == "bin"
    ]
    if not candidates:
        candidates = [path for path in root.rglob(name) if path.is_file()]
    if not candidates:
        raise RuntimeError(f"{name} was not found in the FFmpeg archive.")
    return candidates[0]


def make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def validate_binary(path: Path, expected_name: str) -> None:
    completed = subprocess.run(
        [str(path), "-version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=20,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{expected_name} failed to run:\n{completed.stdout[-2000:]}"
        )


def validate_ffmpeg_features(path: Path) -> None:
    encoder_check = subprocess.run(
        [str(path), "-hide_banner", "-encoders"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=20,
    )
    if encoder_check.returncode != 0 or "libx264" not in encoder_check.stdout:
        raise RuntimeError(
            "The selected FFmpeg build does not provide libx264."
        )


def download(url: str, destination: Path) -> None:
    print(f"Downloading FFmpeg from:\n  {url}")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "VidEditor-RHEL8-bootstrap/1"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        with destination.open("wb") as output:
            shutil.copyfileobj(response, output)


def install(
    tools_dir: Path,
    archive: Path | None,
    url: str,
    expected_sha256: str | None,
) -> None:
    tools_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="videditor-ffmpeg-") as temp_name:
        temp = Path(temp_name)
        archive_path = temp / "ffmpeg.tar.xz"

        if archive is not None:
            archive = archive.expanduser().resolve()
            if not archive.is_file():
                raise RuntimeError(f"Archive does not exist: {archive}")
            print(f"Using local FFmpeg archive:\n  {archive}")
            shutil.copy2(archive, archive_path)
        else:
            download(url, archive_path)

        actual_sha256 = sha256_file(archive_path)
        print(f"Archive SHA256: {actual_sha256}")
        if expected_sha256:
            expected = expected_sha256.strip().lower()
            if actual_sha256.lower() != expected:
                raise RuntimeError(
                    "FFmpeg archive SHA256 does not match the expected value."
                )

        extracted = temp / "extracted"
        extracted.mkdir()
        safe_extract(archive_path, extracted)

        source_ffmpeg = find_binary(extracted, "ffmpeg")
        source_ffprobe = find_binary(extracted, "ffprobe")

        target_ffmpeg = tools_dir / "ffmpeg"
        target_ffprobe = tools_dir / "ffprobe"

        shutil.copy2(source_ffmpeg, target_ffmpeg)
        shutil.copy2(source_ffprobe, target_ffprobe)
        make_executable(target_ffmpeg)
        make_executable(target_ffprobe)

    validate_binary(target_ffmpeg, "ffmpeg")
    validate_binary(target_ffprobe, "ffprobe")
    validate_ffmpeg_features(target_ffmpeg)

    print("FFmpeg runtime installed successfully:")
    print(f"  {target_ffmpeg}")
    print(f"  {target_ffprobe}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install a user-space RHEL8-compatible FFmpeg runtime."
    )
    parser.add_argument(
        "--tools-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=(
            Path(os.environ["VIDEDITOR_FFMPEG_ARCHIVE"])
            if os.environ.get("VIDEDITOR_FFMPEG_ARCHIVE")
            else None
        ),
        help="Use a pre-downloaded .tar.xz archive instead of the network.",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("VIDEDITOR_FFMPEG_URL", DEFAULT_URL),
    )
    parser.add_argument(
        "--sha256",
        default=os.environ.get("VIDEDITOR_FFMPEG_SHA256"),
    )
    args = parser.parse_args()

    try:
        install(
            args.tools_dir.resolve(),
            args.archive,
            args.url,
            args.sha256,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
