"""Consolidate eligible episodic memories into semantic knowledge."""

from __future__ import annotations
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.consolidation import consolidate_memory

if __name__ == "__main__":
    print(json.dumps(consolidate_memory(PROJECT_ROOT / "memory_db"), indent=2, ensure_ascii=False))
