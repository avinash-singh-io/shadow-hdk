"""The ddgs battery's callable: web search behind the component port, consumed (principle 5).

`ddgs` is imported inside the call, so this module loads without it and the battery's `requires`
is what says whether it can run.
"""

from __future__ import annotations

import asyncio
from typing import Any


async def search(query: str, max_results: int = 8) -> dict[str, Any]:
    """Search the web through DuckDuckGo and return titles, addresses and snippets."""
    from ddgs import DDGS  # type: ignore[import-not-found,unused-ignore]

    def run() -> list[dict[str, Any]]:
        with DDGS() as engine:
            return [dict(hit) for hit in engine.text(query, max_results=max_results)]

    hits = await asyncio.to_thread(run)
    return {
        "query": query,
        "results": [
            {"title": h.get("title", ""), "url": h.get("href", ""), "snippet": h.get("body", "")}
            for h in hits
        ],
    }


__all__ = ["search"]
