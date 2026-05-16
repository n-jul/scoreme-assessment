"""JSON input/output for scheduling instances."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.models import Instance, ScheduleResult


def load_instance(path: str | Path) -> Instance:
    with open(path, encoding="utf-8") as f:
        return Instance.from_dict(json.load(f))


def save_instance(instance: Instance, path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(instance.to_dict(), f, indent=2)


def save_result(result: ScheduleResult, path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2)


def write_json(data: dict[str, Any], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
