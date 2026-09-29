import json
import re
from dataclasses import dataclass, field
from typing import Any

from jsonschema import Draft202012Validator


@dataclass
class Checked:
    raw: str
    data: Any = None
    parse_error: str | None = None
    schema_errors: list[str] = field(default_factory=list)

    @property
    def parsed(self) -> bool:
        return self.parse_error is None

    @property
    def valid(self) -> bool:
        return self.parsed and not self.schema_errors


def parse_json(text: str) -> Any:
    if not text.strip():
        raise ValueError("empty reply")
    candidates = [text, *re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate.strip())
        except json.JSONDecodeError:
            continue
    raise ValueError("no JSON object in reply: " + repr(text[:200]))


def schema_errors(data: Any, schema: dict) -> list[str]:
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in Draft202012Validator(schema).iter_errors(data)]


def check(text: str, schema: dict) -> Checked:
    try:
        data = parse_json(text)
    except ValueError as exc:
        return Checked(raw=text, parse_error=str(exc))
    return Checked(raw=text, data=data, schema_errors=schema_errors(data, schema))
