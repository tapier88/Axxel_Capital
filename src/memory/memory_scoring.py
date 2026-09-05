"""Transparent lexical relevance scoring for V0 retrieval."""

from __future__ import annotations

import re
from typing import Any

TOKEN_PATTERN = re.compile(r"[a-záéíóúñ0-9_]+", re.IGNORECASE)


def tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text) if len(token) > 1}


def relevance_score(query: str, memory: dict[str, Any]) -> float:
    query_tokens = tokens(query)
    memory_tokens = tokens(
        " ".join([str(memory.get("content", "")), *map(str, memory.get("tags", []))])
    )
    if not query_tokens or not memory_tokens:
        lexical = 0.0
    else:
        lexical = len(query_tokens & memory_tokens) / len(query_tokens | memory_tokens)
    confidence = float(memory.get("confidence", 0.5))
    return round((0.8 * lexical) + (0.2 * confidence), 6)
