"""There is nothing `harness.toml` can say that the ports cannot (principle 9, D71): every key
the loader accepts maps to a port, a port's argument, or a profile the kernel already means — the
table below, walked against the loader's `KNOWN` and against the tree, so a key added to the file
without a place underneath fails the build, and a key that names something gone fails too.
"""

from __future__ import annotations

import importlib

from shadow_hdk.serve.config import KNOWN

MEANS: dict[str, tuple[str, str, str]] = {
    "environment.root": ("shadow_hdk.adapters.environment", "LocalEnvironment", "open(root=)"),
    "environment.mode": ("shadow_hdk.adapters.environment", "LocalEnvironment", "open(mode=)"),
    "provider.want": ("shadow_hdk.providers", "ready", "want"),
    "store.path": ("shadow_hdk.adapters.basic", "SqliteStore", "the Store port on a file"),
    "store.url": ("shadow_hdk.serve.stores", "stores_for", "the three the url names (D79)"),
    "modes.dir": ("shadow_hdk.adapters.modes", "modes_in", "a ModeRegistry source"),
    "registry.name": ("shadow_hdk.adapters.recording", "SocketOffer", "name="),
    "tools.batteries": ("shadow_hdk.serve.batteries", "open_battery", "each id, opened"),
    "tools.dir": ("shadow_hdk.serve.batteries", "batteries_in", "a BatteryRegistry source"),
    "budget.steps": ("shadow_hdk.kernel", "Ceiling", "max_steps"),
    "budget.seconds": ("shadow_hdk.kernel", "Ceiling", "max_wall_seconds"),
    "budget.cents": ("shadow_hdk.kernel", "Ceiling", "max_cost_cents"),
}
"""`table.key` → (the module, the public name it configures, which part of it)."""


def test_every_known_key_means_something_underneath() -> None:
    known = {f"{table}.{key}" for table, keys in KNOWN.items() for key in keys}
    unmapped = sorted(known - set(MEANS))
    assert not unmapped, f"harness.toml accepts keys that map to no port or profile: {unmapped}"
    stale = sorted(set(MEANS) - known)
    assert not stale, f"the table names keys the loader no longer accepts: {stale}"


def test_every_target_in_the_table_exists_and_is_public() -> None:
    for key, (module, name, _part) in MEANS.items():
        loaded = importlib.import_module(module)
        assert hasattr(loaded, name), f"{key} maps to {module}.{name}, which does not exist"
        assert name in getattr(loaded, "__all__", ()), f"{key} maps to {module}.{name}, not public"


def test_the_walk_refuses_a_key_without_a_meaning() -> None:
    pretend = {**KNOWN, "vocabulary": {"labels"}}
    known = {f"{table}.{key}" for table, keys in pretend.items() for key in keys}
    assert sorted(known - set(MEANS)) == ["vocabulary.labels"]
