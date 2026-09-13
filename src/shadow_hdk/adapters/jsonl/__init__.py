"""A coding CLI that answers in line-delimited JSON, driven as a governed agent provider (D39).

One adapter, many CLIs. What differs between Claude Code and Codex is **names** — which key holds
the event type, which type carries assistant text, where the text is — and the names live in each
provider's own TOML as a `Dialect`. Adding a CLI that speaks this way costs a file.
"""

from shadow_hdk.adapters.jsonl.paths import read_at, texts_at
from shadow_hdk.adapters.jsonl.session import JsonlSession
from shadow_hdk.adapters.jsonl.transport import (
    JsonlProvider,
    UngovernableProvider,
    argv_for,
    mcp_config_for,
    open_agent,
)

__all__ = [
    "JsonlProvider",
    "JsonlSession",
    "UngovernableProvider",
    "argv_for",
    "mcp_config_for",
    "open_agent",
    "read_at",
    "texts_at",
]
