import json
from pathlib import Path
from typing import Any, Dict

from src.project.model import validate_project


def save_project(path: Path, data: Dict[str, Any]) -> None:
    validate_project(data)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
        sort_keys=False,
    )
    temporary.write_text(payload + "\n", encoding="utf-8")
    temporary.replace(path)


def load_project(path: Path) -> Dict[str, Any]:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_project(data)
    return data
