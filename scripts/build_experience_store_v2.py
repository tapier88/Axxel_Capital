"""Build the immutable GOLD M1 Experience Store V2 from local raw manifests."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from src.data.pipeline_v2 import build_experience_store_v2


def _single(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one manifest for {pattern}; found {len(matches)}")
    return matches[0]


if __name__ == "__main__":
    project = PROJECT_ROOT
    m1 = _single(project, "data/raw/gold_m1/**/*.manifest.json")
    ticks = _single(project, "data/raw/gold_ticks/**/*.manifest.json")
    print(json.dumps(build_experience_store_v2(project, m1, ticks), indent=2))
