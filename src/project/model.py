from typing import Any, Dict


PROJECT_FORMAT = "vid-editor-project"
PROJECT_VERSION = 1


def empty_project() -> Dict[str, Any]:
    return {
        "format": PROJECT_FORMAT,
        "version": PROJECT_VERSION,
        "raw_cutter": {},
        "assembly": {
            "clips": [],
            "text_overlays": [],
        },
    }


def validate_project(data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("Project root must be a JSON object.")

    if data.get("format") != PROJECT_FORMAT:
        raise ValueError("This is not a Vid Editor project file.")

    version = data.get("version")
    if version != PROJECT_VERSION:
        raise ValueError(
            f"Unsupported project version: {version!r}. "
            f"Expected version {PROJECT_VERSION}."
        )

    if not isinstance(data.get("raw_cutter", {}), dict):
        raise ValueError("Project raw_cutter section must be an object.")

    assembly = data.get("assembly", {})
    if not isinstance(assembly, dict):
        raise ValueError("Project assembly section must be an object.")

    clips = assembly.get("clips", [])
    overlays = assembly.get("text_overlays", [])
    if not isinstance(clips, list) or not isinstance(overlays, list):
        raise ValueError("Project clips and text_overlays must be arrays.")
