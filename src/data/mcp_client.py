"""Minimal read-only client for the configured MarketData MCP server."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any


class MarketDataClient:
    def __init__(self, project_root: Path | str):
        config = json.loads((Path(project_root) / ".mcp.json").read_text(encoding="utf-8"))
        server = config["mcpServers"]["marketdata"]
        self.url = server["url"]
        self.authorization = server["headers"]["Authorization"]

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        }).encode("utf-8")
        request = urllib.request.Request(
            self.url, data=payload, method="POST",
            headers={
                "Authorization": self.authorization,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-06-18",
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            text = response.read().decode("utf-8")
        if text.startswith("event:"):
            text = "\n".join(line[6:] for line in text.splitlines() if line.startswith("data: "))
        envelope = json.loads(text)
        if "error" in envelope:
            raise RuntimeError(envelope["error"].get("message", "MCP request failed"))
        result = envelope["result"]
        if result.get("isError"):
            raise RuntimeError("; ".join(item.get("text", "") for item in result.get("content", [])))
        structured = result.get("structuredContent")
        if structured is None:
            for item in reversed(result.get("content", [])):
                if item.get("type") == "text":
                    try:
                        return json.loads(item["text"])
                    except json.JSONDecodeError:
                        continue
            raise RuntimeError("MCP response has no structured JSON content")
        return structured

    def history(self, symbol: str, timeframe: str, start: str, end: str) -> dict[str, Any]:
        return self.call("marketdata_symbol_history", {
            "symbol": symbol, "timeframe": timeframe, "from": start, "to": end,
        })
