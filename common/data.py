import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"


def load_json(name: str) -> Any:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def read_text(name: str) -> str:
    return (DATA / name).read_text(encoding="utf-8")


def save_output(name: str, payload: Any) -> Path:
    OUTPUTS.mkdir(exist_ok=True)
    path = OUTPUTS / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
