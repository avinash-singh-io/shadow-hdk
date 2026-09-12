"""The wire is held to parity with in-process, mechanically (D51).

Phase 21 found the agent adapter could not run over the wire, and nothing had said so: four context
methods did not cross and no test, table or document recorded which. This file is the table, and
the walk that makes it a build failure.

**Three rules.**

1. Every public method on `RunContext` is either **overridden** by `WireRunContext` to cross, or
   named below with the reason it does not. A new method on the context cannot be added without
   answering the question.
2. Every kind in the `Event` union is in the wire's published schemas, and `Item` is published —
   a client in another language can read everything a run produces.
3. No adapter calls a **synchronous-only** context method. `remaining()`, `floor_met()` and
   `spawn_options()` raise across a wire; their `_now` forms work on both sides, and an adapter
   written once must run both sides.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from shadow_hdk.runtime import RunContext
from shadow_hdk.wire.context import WireRunContext
from shadow_hdk.wire.schemas import published

ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = ROOT / "packages" / "adapters"

NOT_CROSSING: dict[str, str] = {
    "remaining": "synchronous; `remaining_now()` crosses",
    "floor_met": "synchronous; `floor_met_now()` crosses",
    "spawn_options": "synchronous; `spawn_options_now()` answers with host-local options",
    "context": "builds a governance `Context` locally from what the host holds",
    "announce_held": "runtime-internal: a child announces itself where the record is",
    "checkpointer": "the runtime's, and it cannot travel; a crossed spawn uses the runtime's own",
    "idempotency_key": "derived from run and step, which the crossed context already carries",
    "announce_child": "runtime-internal: the drive announces a child where the record is",
    "forward": "runtime-internal: the drive forwards a child's events into the parent's stream",
    "reserve": "runtime-internal: the meter reserves for a child, runtime-side on a crossed spawn",
    "settle": "runtime-internal: the meter settles what a child did not use",
    "unreachable": "a runtime-side fact; a crossed component meets it as a refusal",
    "accept_answer": "runtime-internal: turns the host's answer into a judgement where the record "
    "and the rule registry are; a crossed request_approval receives the judgement already made",
    "take_kept": "runtime-internal: the executor collects what a component kept before it parks",
    "resuming": "runtime-internal: the executor hands a resumed step its answer and what it kept",
    "resumed_done": "runtime-internal: the executor clears that after the invoke",
    "activity_now": "synchronous convenience over `activity` for a reader task; `activity` crosses",
    "forward_activity": "runtime-internal: the drive forwards a child's activity to the root",
}
"""Method → why it does not cross. Every entry is a claim; an entry for a method that has since
been made to cross is refused by the third test below."""

SYNC_ONLY = ("remaining", "floor_met", "spawn_options")


def _public(cls: type) -> set[str]:
    return {
        name
        for name, _ in inspect.getmembers(cls)
        if not name.startswith("_") and name not in ("ports", "run_id", "step", "children")
    }


def _overridden() -> set[str]:
    return {name for name in vars(WireRunContext) if not name.startswith("_")}


def _sync_only_calls(source: Path) -> list[str]:
    found: list[str] = []
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in SYNC_ONLY
        ):
            where = source.relative_to(ROOT) if source.is_relative_to(ROOT) else source.name
            found.append(f"{where}:{node.lineno}: .{node.func.attr}()")
    return found


# --------------------------------------------------------------------------- the guards


def test_every_context_method_crosses_or_says_why() -> None:
    methods = _public(RunContext)
    crossing = _overridden()
    unaccounted = sorted(methods - crossing - set(NOT_CROSSING))

    assert not unaccounted, (
        f"these RunContext methods neither cross the wire nor say why: {unaccounted}"
    )


def test_nothing_is_excused_that_actually_crosses() -> None:
    """An entry left behind after a method was made to cross keeps the table looking complete."""
    stale = sorted(name for name in NOT_CROSSING if name in _overridden() and name not in SYNC_ONLY)

    assert not stale, f"listed as not crossing, but WireRunContext overrides them: {stale}"


def test_every_event_kind_and_the_projection_are_published() -> None:
    from typing import get_args

    from shadow_hdk.kernel.events import Event

    kinds = {arm.__dataclass_fields__["kind"].default for arm in get_args(get_args(Event)[0])}
    schemas = published()

    assert "Event" in schemas and "Item" in schemas
    event_schema = str(schemas["Event"])
    missing = sorted(
        k for k in kinds if f'"{k}"' not in event_schema and f"'{k}'" not in event_schema
    )
    assert not missing, f"event kinds a client cannot read from the published schema: {missing}"


def test_no_adapter_calls_a_synchronous_only_context_method() -> None:
    """The rule an adapter written once must follow to run both sides."""
    offenders: list[str] = []
    for source in sorted(ADAPTERS.glob("*/src/**/*.py")):
        offenders += _sync_only_calls(source)

    assert not offenders, "\n  ".join(
        ["adapters calling a method that raises over a wire:", *offenders]
    )


# --------------------------------------------------------------------------- anti-vacuity


def test_the_walks_see_what_they_look_for(tmp_path: Path) -> None:
    assert len(_public(RunContext)) >= 8, _public(RunContext)
    assert "visible" in _overridden() and "reasoning" in _overridden()

    offending = tmp_path / "m.py"
    offending.write_text(
        "async def f(ctx):\n    return ctx.remaining().ceiling\n", encoding="utf-8"
    )
    clean = tmp_path / "n.py"
    clean.write_text(
        "async def f(ctx):\n    return (await ctx.remaining_now()).ceiling\n", encoding="utf-8"
    )
    assert len(_sync_only_calls(offending)) == 1
    assert _sync_only_calls(clean) == []
