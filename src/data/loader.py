"""Load and validate the outer shape of raw market-data artifacts."""

from __future__ import annotations
from pathlib import Path
from typing import Any
from src.utils.serialization import read_json


def load_raw_dataset(path: Path | str) -> dict[str, Any]:
    raise PermissionError("Direct RAW loading retired; use DataEngine.query(certified_id).")
