"""What `serve` needs from `harness.toml` now (Phase 26); the full facade is Phase 27.

Every key maps to something a port or a profile already means; an unknown key is refused,
because a typo that quietly selects nothing is worse than an error.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shadow_hdk.kernel import Ceiling, Floor, Lease

KNOWN: dict[str, set[str]] = {
    "environment": {"root", "mode"},
    "provider": {"want", "idle_seconds"},
    "store": {"path", "url"},
    "modes": {"dir"},
    "registry": {"name"},
    "tools": {"batteries", "dir"},
    "budget": {"steps", "seconds", "cents"},
}


@dataclass(frozen=True)
class Budget:
    """What one thread may spend — the file's and the facade's word for the kernel's `Lease`
    (the owner's: `budget` where a product reads it, `Lease` underneath). The default is small
    enough to notice on a subscription."""

    steps: int = 400
    seconds: int = 3600
    cents: int | None = 500

    def lease(self) -> Lease:
        return Lease(
            Ceiling(max_steps=self.steps, max_wall_seconds=self.seconds, max_cost_cents=self.cents),
            Floor(0),
        )


@dataclass(frozen=True)
class Settings:
    root: Path
    mode: str = "workspace-write"
    """The thread's default mode id (D64, D76): a shipped one — `read-only`, `ask`,
    `workspace-write`, `full` — or one from files or the store. The sandbox mode follows from it;
    an unknown id is refused at `open`, against the registry read then."""
    want: str | None = None
    idle_seconds: float | None = None
    """`[provider] idle_seconds = 1800`: a thread's provider session closed after that long
    without a turn and reopened on its own session id at the next (D94); nothing keeps it."""
    store: str | None = None
    """Where the record lives (D79): a url — `sqlite:///…/live.sqlite`, `postgresql://…` — that
    fills the store, the thread store and the checkpointer at once (`serve.stores_for`); `None`
    is memory, for the process. `[store] path = "live.sqlite"` is sugar for the sqlite url."""
    modes_dir: Path | None = None
    registry_name: str = "tools"
    batteries: tuple[str, ...] = ()
    """Battery ids switched on (D70): `[tools] batteries = ["wigolo"]`."""
    batteries_dir: Path | None = None
    """A directory of battery files read beside the shipped ones: `[tools] dir = "batteries"`."""
    budget: Budget = Budget()
    """`[budget] steps = 400  seconds = 3600  cents = 500` — the thread's lease, in the file's
    word."""


def store_url(given: dict[str, Any], *, base: Path, name: str = "harness.toml") -> str | None:
    """`[store]` as one url (D79). `path` is the sqlite sugar; `url` is any scheme `stores_for`
    knows; a relative sqlite path, either way, is relative to the file like every path in it."""
    path, url = given.get("path"), given.get("url")
    if path and url:
        raise ValueError(f"{name}: [store] takes one of path or url, not both")
    if path:
        return as_store_url(str(path), base=base)
    if url:
        return as_store_url(str(url), base=base)
    return None


def as_store_url(given: str, *, base: Path) -> str:
    """A path or a url, as a url: a bare path is a sqlite file; a sqlite url whose path is
    relative is anchored at `base`; anything else is handed on as it came."""
    if given.startswith("sqlite:///"):
        rest = given[len("sqlite:///") :]
        return f"sqlite:///{(base / rest).resolve()}" if not rest.startswith("/") else given
    if "://" in given:
        return given
    return f"sqlite:///{(base / given).resolve()}"


def load_settings(path: Path | str) -> Settings:
    where = Path(path)
    raw: dict[str, Any] = tomllib.loads(where.read_text(encoding="utf-8"))
    base = where.resolve().parent
    for table, keys in raw.items():
        if table not in KNOWN:
            raise ValueError(f"{where.name}: unknown table [{table}]; known: {sorted(KNOWN)}")
        if not isinstance(keys, dict):
            raise ValueError(f"{where.name}: [{table}] must be a table")
        if unknown := sorted(set(keys) - KNOWN[table]):
            raise ValueError(
                f"{where.name}: unknown key(s) in [{table}]: {', '.join(unknown)}; "
                f"known: {sorted(KNOWN[table])}"
            )
    environment = raw.get("environment", {})
    # The thread's default *mode id* (D64, D76) — a shipped one (`read-only`, `ask`,
    # `workspace-write`, `full`) or one from files or the store; the sandbox mode follows from
    # it. Unknown ids are refused at `open`, against the registry read then (D66), not here.
    mode = str(environment.get("mode", "workspace-write"))
    if not mode:
        raise ValueError(f"{where.name}: mode is empty; name a mode id")
    root = (base / str(environment.get("root", "."))).resolve()
    store = store_url(raw.get("store", {}), base=base, name=where.name)
    modes_dir = raw.get("modes", {}).get("dir")
    want = raw.get("provider", {}).get("want") or None
    idle = raw.get("provider", {}).get("idle_seconds")
    if idle is not None and (not isinstance(idle, int | float) or isinstance(idle, bool)):
        raise ValueError(f"{where.name}: [provider] idle_seconds must be a number of seconds")
    tools = raw.get("tools", {})
    wanted = tools.get("batteries", [])
    if not isinstance(wanted, list) or not all(isinstance(b, str) for b in wanted):
        raise ValueError(f"{where.name}: [tools] batteries must be a list of battery ids")
    batteries_dir = tools.get("dir")
    given = raw.get("budget", {})
    for key in ("steps", "seconds", "cents"):
        if key in given and not isinstance(given[key], int):
            raise ValueError(f"{where.name}: [budget] {key} must be a whole number")
    budget = Budget(
        steps=int(given.get("steps", Budget.steps)),
        seconds=int(given.get("seconds", Budget.seconds)),
        cents=int(given["cents"]) if "cents" in given else Budget.cents,
    )
    return Settings(
        root=root,
        mode=mode,
        want=str(want) if want else None,
        idle_seconds=float(idle) if idle is not None else None,
        store=store,
        modes_dir=(base / str(modes_dir)).resolve() if modes_dir else None,
        registry_name=str(raw.get("registry", {}).get("name", "tools") or "tools"),
        batteries=tuple(wanted),
        batteries_dir=(base / str(batteries_dir)).resolve() if batteries_dir else None,
        budget=budget,
    )


__all__ = ["KNOWN", "Budget", "Settings", "as_store_url", "load_settings", "store_url"]
