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
from shadow_hdk.runtime.environment import Mode as EnvironmentMode

KNOWN: dict[str, set[str]] = {
    "environment": {"root", "mode"},
    "provider": {"want"},
    "store": {"path"},
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
    mode: EnvironmentMode = "workspace-write"
    want: str | None = None
    store: Path | None = None
    modes_dir: Path | None = None
    registry_name: str = "tools"
    batteries: tuple[str, ...] = ()
    """Battery ids switched on (D70): `[tools] batteries = ["wigolo"]`."""
    batteries_dir: Path | None = None
    """A directory of battery files read beside the shipped ones: `[tools] dir = "batteries"`."""
    budget: Budget = Budget()
    """`[budget] steps = 400  seconds = 3600  cents = 500` — the thread's lease, in the file's
    word."""


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
    mode = str(environment.get("mode", "workspace-write"))
    if mode not in ("read-only", "workspace-write", "full"):
        raise ValueError(f"{where.name}: mode {mode!r} is not read-only, workspace-write or full")
    root = (base / str(environment.get("root", "."))).resolve()
    store = raw.get("store", {}).get("path")
    modes_dir = raw.get("modes", {}).get("dir")
    want = raw.get("provider", {}).get("want") or None
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
        mode=mode,  # type: ignore[arg-type]
        want=str(want) if want else None,
        store=(base / str(store)).resolve() if store else None,
        modes_dir=(base / str(modes_dir)).resolve() if modes_dir else None,
        registry_name=str(raw.get("registry", {}).get("name", "tools") or "tools"),
        batteries=tuple(wanted),
        batteries_dir=(base / str(batteries_dir)).resolve() if batteries_dir else None,
        budget=budget,
    )


__all__ = ["KNOWN", "Budget", "Settings", "load_settings"]
