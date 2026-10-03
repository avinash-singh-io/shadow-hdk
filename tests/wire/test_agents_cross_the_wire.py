"""`agents/list`, and which agent a thread resolved to (D177, phase 64).

The listing completes a symmetry: `modes/list`, `rules/list`, `skills/list`, `tools/list`,
`batteries/list` and `providers/list` all existed; agents had none, so a product could store them
and select them but not show a person what there was to choose.

And `agent` on the thread's own description, because lane P carries a resolved snapshot — agent,
instructions, skills, version, content hash — so a person's machine can cache by hash. They cannot
build one if the kit will not say which agent a run resolved to.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import ModelResponse
from shadow_hdk.serve import ServeHost, Settings
from shadow_hdk.wire.protocol import AGENTS_LIST
from shadow_hdk.wire.sides import loopback

pytestmark = pytest.mark.anyio

A_REVIEWER = {"name": "reviewer", "system": "REVIEWER-ROLE: you review a change."}
A_BUILDER = {"name": "builder", "system": "BUILDER-ROLE: you write the change."}


class Cli:
    """A handed CLI port: the wire check must also run on machines with no vendor CLI."""

    async def open(self, **kw: Any) -> Any:
        return self

    async def turn(self, prompt: str) -> Any:
        from shadow_hdk.kernel import Turn

        return Turn(text="done")

    async def close(self) -> None:
        return None

    async def stream(self, prompt: str) -> Any:  # pragma: no cover
        raise NotImplementedError


class Quiet:
    async def complete(self, request: Any) -> ModelResponse:
        return ModelResponse(text="done")

    async def stream(self, request: Any) -> Any:  # pragma: no cover
        from shadow_hdk.kernel.ports import ModelChunk

        yield ModelChunk(text="done", done=True)


async def a_host(where: Path) -> ServeHost:
    host = ServeHost(
        Settings(root=where, store=f"sqlite:///{where / 'h.db'}"), model=cast(Any, Quiet())
    )
    for row in (A_REVIEWER, A_BUILDER):
        await host.store.put("agents", row["name"], row)
    await host.store.put(
        "modes", "reviewing", {"id": "reviewing", "policy": "workspace-write", "agent": "reviewer"}
    )
    return host


# ------------------------------------------------------------------ the listing


async def test_agents_list_says_what_a_product_may_run(tmp_path: Path) -> None:
    host = await a_host(tmp_path)

    async with loopback(threads=host) as (side, _runtime):
        await side.initialize()
        said = await side.peer.call(AGENTS_LIST, {})

    names = [a["name"] for a in said["agents"]]
    assert "reviewer" in names and "builder" in names, names
    assert "single" in names, "the shipped library is listed beside the product's own"


async def test_each_one_carries_a_line_a_person_can_choose_by(tmp_path: Path) -> None:
    host = await a_host(tmp_path)

    async with loopback(threads=host) as (side, _runtime):
        await side.initialize()
        said = await side.peer.call(AGENTS_LIST, {})

    reviewer = next(a for a in said["agents"] if a["name"] == "reviewer")
    assert reviewer["description"].startswith("REVIEWER-ROLE"), reviewer


async def test_the_listing_is_sorted_so_a_page_does_not_reshuffle(tmp_path: Path) -> None:
    host = await a_host(tmp_path)

    async with loopback(threads=host) as (side, _runtime):
        await side.initialize()
        said = await side.peer.call(AGENTS_LIST, {})

    names = [a["name"] for a in said["agents"]]
    assert names == sorted(names), names


# ------------------------------------------------------------------ and what a thread resolved to


async def test_a_thread_says_which_agent_it_resolved_to(tmp_path: Path) -> None:
    """D177. Without this a product cannot build the resolved snapshot it caches by hash."""
    host = await a_host(tmp_path)

    async with loopback(threads=host) as (side, _runtime):
        await side.initialize()
        started = await side.peer.call("thread/start", {"root": str(tmp_path), "mode": "reviewing"})
        await side.peer.call("thread/close", {"thread_id": started["thread_id"]})

    assert started["agent"] == "reviewer", started


async def test_a_thread_overriding_the_mode_says_the_override(tmp_path: Path) -> None:
    host = await a_host(tmp_path)

    async with loopback(threads=host) as (side, _runtime):
        await side.initialize()
        started = await side.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "reviewing", "agent": "builder"}
        )
        await side.peer.call("thread/close", {"thread_id": started["thread_id"]})

    assert started["agent"] == "builder", started


async def test_a_thread_naming_nothing_says_single(tmp_path: Path) -> None:
    """Empty would read as *we do not know*; `single` is what actually ran."""
    host = await a_host(tmp_path)
    await host.store.put("modes", "plain", {"id": "plain", "policy": "workspace-write"})

    async with loopback(threads=host) as (side, _runtime):
        await side.initialize()
        started = await side.peer.call("thread/start", {"root": str(tmp_path), "mode": "plain"})
        await side.peer.call("thread/close", {"thread_id": started["thread_id"]})

    assert started["agent"] == "single", started


# ------------------------------------- and what it asked for and could not have (H11-A, phase 66)


async def test_a_thread_says_which_agent_it_could_not_run(tmp_path: Path) -> None:
    """A product over the wire needs this exactly as much as one in process. A host with no model is
    every CLI host: the agent is dropped there because the CLI owns its own loop, and before phase
    66 that was silent — `agent` answered `""`, which means *no agent applies*, and said nothing
    about
    the request."""
    host = ServeHost(
        Settings(root=tmp_path, store=f"sqlite:///{tmp_path / 'h.db'}"), agent=cast(Any, Cli())
    )
    await host.store.put("agents", "reviewer", dict(A_REVIEWER))
    await host.store.put(
        "modes", "reviewing", {"id": "reviewing", "policy": "workspace-write", "agent": "reviewer"}
    )
    try:
        async with loopback(threads=host) as (side, _runtime):
            await side.initialize()
            started = await side.peer.call(
                "thread/start", {"root": str(tmp_path), "mode": "reviewing"}
            )
            await side.peer.call("thread/close", {"thread_id": started["thread_id"]})
    finally:
        await host.aclose()

    assert started["agent_unhonoured"] == "reviewer", started
    assert started["agent"] == "", "exactly one of the two is ever set"


async def test_a_thread_that_ran_its_agent_reports_nothing_unhonoured(tmp_path: Path) -> None:
    """Paired against the above, through the same door: this host has a model, so the agent runs."""
    host = await a_host(tmp_path)

    async with loopback(threads=host) as (side, _runtime):
        await side.initialize()
        started = await side.peer.call("thread/start", {"root": str(tmp_path), "mode": "reviewing"})
        await side.peer.call("thread/close", {"thread_id": started["thread_id"]})

    assert started["agent"] == "reviewer", started
    assert started["agent_unhonoured"] == "", started
