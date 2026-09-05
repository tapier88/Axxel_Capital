"""Auditable JSON repositories used by research, experience and memory."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from src.utils.serialization import atomic_write_json, read_json


class JsonRepository:
    def __init__(self, path: Path | str, id_field: str = "id"):
        self.path = Path(path)
        self.id_field = id_field

    def all(self) -> list[dict[str, Any]]:
        records = read_json(self.path, [])
        if not isinstance(records, list):
            raise ValueError(f"Repository {self.path} must contain a JSON array")
        return records

    def add(self, record: dict[str, Any]) -> dict[str, Any]:
        identifier = record.get(self.id_field)
        if not identifier:
            raise ValueError(f"Record requires {self.id_field}")
        records = self.all()
        if any(item.get(self.id_field) == identifier for item in records):
            raise ValueError(f"Duplicate identifier: {identifier}")
        records.append(record)
        atomic_write_json(self.path, records)
        return record

    def update(self, identifier: str, changes: dict[str, Any]) -> dict[str, Any]:
        records = self.all()
        for index, record in enumerate(records):
            if record.get(self.id_field) == identifier:
                updated = {**record, **changes, self.id_field: identifier}
                records[index] = updated
                atomic_write_json(self.path, records)
                return updated
        raise KeyError(identifier)

    def find(self, predicate: Callable[[dict[str, Any]], bool]) -> list[dict[str, Any]]:
        return [record for record in self.all() if predicate(record)]
