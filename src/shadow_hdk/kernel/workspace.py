"""A workspace is one or many roots (D76): what a conversation works on, chosen by the product.

VS Code's multi-root workspace, Claude Code's `--add-dir`, Codex's `writable_roots` — the same
shape. The **primary** root is where a relative path resolves; every other root is addressed by
its name (`sales/notes.md`). The environment confines to all of them and proves it; the policy's
scope stays `workspace` — a rule that wants to tell roots apart names the path (D65).

Pure data: a path here is a string the runtime resolves. The kernel touches no filesystem, so
whether two roots nest is the environment's to say when it opens on them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Root:
    """One directory a thread works on, and the name it is addressed by."""

    name: str
    path: str

    def __post_init__(self) -> None:
        if not self.name or "/" in self.name or self.name in (".", ".."):
            raise ValueError(f"a root's name is one path segment, not {self.name!r}")
        if not self.path:
            raise ValueError(f"root {self.name!r} names no directory")


@dataclass(frozen=True)
class Workspace:
    """The roots, in order; the first is the primary."""

    roots: tuple[Root, ...]

    def __post_init__(self) -> None:
        if not self.roots:
            raise ValueError("a workspace has at least one root")
        names = [r.name for r in self.roots]
        if len(set(names)) != len(names):
            raise ValueError(f"two roots have the same name: {names}")
        paths = [r.path.rstrip("/") for r in self.roots]
        if len(set(paths)) != len(paths):
            raise ValueError("two roots name the same directory")

    @classmethod
    def of(cls, path: Any, name: str = "") -> Workspace:
        """One root, named after its directory unless told otherwise."""
        where = str(path).rstrip("/")
        return cls((Root(name or where.rsplit("/", 1)[-1] or "workspace", where),))

    @property
    def primary(self) -> Root:
        return self.roots[0]

    def named(self, name: str) -> Root:
        for root in self.roots:
            if root.name == name:
                return root
        raise KeyError(name)

    def has(self, name: str) -> bool:
        return any(r.name == name for r in self.roots)

    def with_root(self, root: Root) -> Workspace:
        return Workspace((*self.roots, root))

    def describe(self) -> str:
        """One line the tools carry: the roots, the primary marked, and how to address the rest."""
        parts = [f"{r.name} (primary)" if i == 0 else r.name for i, r in enumerate(self.roots)]
        line = "Roots: " + ", ".join(parts) + "."
        if len(self.roots) > 1:
            other = self.roots[1].name
            line += (
                f" A path is relative to the primary; address another root by name, `{other}/…`."
            )
        return line

    def as_json(self) -> list[dict[str, Any]]:
        return [{"name": r.name, "path": r.path} for r in self.roots]

    @classmethod
    def from_json(cls, given: Any) -> Workspace:
        return cls(tuple(Root(str(r["name"]), str(r["path"])) for r in given))


__all__ = ["Root", "Workspace"]
