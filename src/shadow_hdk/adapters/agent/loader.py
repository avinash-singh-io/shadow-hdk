"""A pattern is a file (D17).

`09` §5: *the framework ships a small set and a team adds its own **the same way it adds a skill**.
Nothing in the runtime knows the names.* A dataclass in a module satisfies the second half and fails
the first — adding a pattern would mean editing the package. So the shipped patterns live in
`library/` as TOML, and `load_pattern` is the same call for ours and for anybody's.

**TOML** because a role file is multi-line prose, which JSON cannot hold without escaping it into
unreadability, and because `tomllib` has been in the standard library since 3.11 — so the format
costs no dependency. YAML would cost one and buy ambiguity.

Every refusal here names the word that is wrong, because the reader is the person who wrote the
file. A traceback about a dict is no use to them.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import replace
from importlib import resources
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.agent.pattern import META_TOOLS, Pattern
from shadow_hdk.kernel.contracts import load
from shadow_hdk.kernel.effects import EffectProfile

KEYS = frozenset(
    {
        "name",
        "system",
        "meta_tools",
        "tool_names",
        "ceiling",
        "max_turns",
        "nudge",
        "catalogue_threshold",
    }
)
REQUIRED = ("name", "system")
LIBRARY = "library"


def pattern_from(data: dict[str, Any], *, where: str) -> Pattern:
    """Build a `Pattern` from parsed TOML, refusing anything a person should fix."""
    unknown = set(data) - KEYS
    if unknown:
        raise ValueError(
            f"{where}: unknown key(s) {sorted(unknown)}; known keys are {sorted(KEYS)}"
        )
    for key in REQUIRED:
        if not data.get(key):
            raise ValueError(f"{where}: needs a {key!r}")

    meta = frozenset(data.get("meta_tools", ("propose", "done")))
    stray = meta - META_TOOLS
    if stray:
        # Ahead of `Pattern.__post_init__`, which raises the same thing without saying which file.
        raise ValueError(f"{where}: unknown meta-tool(s) {sorted(stray)}")

    tools = data.get("tool_names")
    ceiling = data.get("ceiling")
    pattern = Pattern(
        name=str(data["name"]),
        system=str(data["system"]).strip(),
        meta_tools=meta,
        tool_names=None if tools is None else frozenset(tools),
        ceiling=None if ceiling is None else load(json.dumps(ceiling), EffectProfile),
    )
    # The optional fields keep the dataclass's defaults unless the file names them.
    if "max_turns" in data:
        pattern = replace(pattern, max_turns=int(data["max_turns"]))
    if "catalogue_threshold" in data:
        pattern = replace(pattern, catalogue_threshold=int(data["catalogue_threshold"]))
    if "nudge" in data:
        pattern = replace(pattern, nudge=str(data["nudge"]).strip())
    return pattern


def load_pattern(path: str | Path) -> Pattern:
    """Read one pattern file. The **name is in the file**: a pattern renamed by moving it is a
    pattern that cannot be cited."""
    where = str(path)
    try:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as broken:
        raise ValueError(f"{where}: not readable as TOML — {broken}") from broken
    return pattern_from(data, where=where)


def shipped() -> dict[str, Pattern]:
    """The patterns the framework ships, read from `library/` at import of nothing in particular.

    Read from the package rather than a path on disk, so an installed wheel and a checkout behave
    the same.
    """
    found: dict[str, Pattern] = {}
    root = resources.files("shadow_hdk.adapters.agent").joinpath(LIBRARY)
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        if not entry.name.endswith(".toml"):
            continue
        data = tomllib.loads(entry.read_text(encoding="utf-8"))
        pattern = pattern_from(data, where=f"{LIBRARY}/{entry.name}")
        found[pattern.name] = pattern
    return found


__all__ = ["KEYS", "load_pattern", "pattern_from", "shipped"]
