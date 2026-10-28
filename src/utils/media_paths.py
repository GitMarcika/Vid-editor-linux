from pathlib import PurePosixPath, PureWindowsPath


def media_reference_basename(reference: str) -> str:
    text = str(reference).strip()
    if not text:
        return ""

    windows_name = PureWindowsPath(text).name
    posix_name = PurePosixPath(text).name

    if "\\" in text:
        return windows_name
    return posix_name or windows_name
