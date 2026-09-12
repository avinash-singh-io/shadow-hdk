"""Modes from files, in the shape a person writes (D66; OpenCode's shape).

`reviewer.md`:

    ---
    name: Reviewer
    description: Reads, never writes.
    policy: read-only
    model: sonnet
    effort: high
    ---
    You review code. Point at lines; do not edit.

The file's stem is the id; the body is the behaviour's `append_system` (or `system`, when the
frontmatter says `prompt: system`); the frontmatter's `model`, `effort`, `temperature`, `tools`
are the behaviour's; `policy` names a shipped policy. `builder.toml` is the same document in
TOML with a `[behaviour]` table. The directory is read on every `modes()`, which is what makes a
file written now a mode at the next read.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.modes.registry import ModeSpec, mode_from_document

BEHAVIOUR_KEYS = ("model", "effort", "temperature", "append_system", "system")


def _frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """A small, honest subset of YAML: `key: value` lines between `---` fences. Values are strings,
    numbers when they parse, lists when written `[a, b]`. Anything cleverer is a TOML file."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        raise ValueError("frontmatter opened with --- and never closed")
    head, body = parts[0][3:], parts[1]
    found: dict[str, Any] = {}
    for line in head.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"frontmatter line is not `key: value`: {line!r}")
        key, _, value = line.partition(":")
        found[key.strip()] = _scalar(value.strip())
    return found, body.lstrip("\n")


def _scalar(raw: str) -> Any:
    if raw.startswith("[") and raw.endswith("]"):
        return [_scalar(part.strip()) for part in raw[1:-1].split(",") if part.strip()]
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _document_from_markdown(path: Path) -> dict[str, Any]:
    head, body = _frontmatter(path.read_text(encoding="utf-8"))
    behaviour: dict[str, Any] = {}
    for key in BEHAVIOUR_KEYS:
        if key in head:
            behaviour[key] = head.pop(key)
    if "tools" in head:
        behaviour["tools_offered"] = list(head.pop("tools"))
    prompt_as = head.pop("prompt", "append")
    if body.strip():
        behaviour["system" if prompt_as == "system" else "append_system"] = body.strip()
    return {
        "id": head.pop("id", path.stem),
        "name": head.pop("name", ""),
        "description": head.pop("description", ""),
        "policy": head.pop("policy", ""),
        "behaviour": behaviour,
        **{k: v for k, v in head.items()},
    }


def _document_from_toml(path: Path) -> dict[str, Any]:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    raw.setdefault("id", path.stem)
    return raw


class FileModes:
    """Every `*.md` and `*.toml` under one directory, read on every call."""

    def __init__(self, where: Path | str) -> None:
        self._where = Path(where)
        self._problems: tuple[str, ...] = ()

    async def modes(self) -> tuple[ModeSpec, ...]:
        modes: list[ModeSpec] = []
        problems: list[str] = []
        if self._where.is_dir():
            for path in sorted(self._where.iterdir()):
                if path.suffix not in (".md", ".toml"):
                    continue
                try:
                    document = (
                        _document_from_markdown(path)
                        if path.suffix == ".md"
                        else _document_from_toml(path)
                    )
                    modes.append(mode_from_document(document, source="file"))
                except (ValueError, OSError, tomllib.TOMLDecodeError) as wrong:
                    problems.append(f"{path.name}: {wrong}")
        self._problems = tuple(problems)
        return tuple(modes)

    async def problems(self) -> tuple[str, ...]:
        return self._problems


def modes_in(where: Path | str) -> FileModes:
    return FileModes(where)


__all__ = ["FileModes", "modes_in"]
