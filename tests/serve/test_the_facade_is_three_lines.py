"""The facade (Phase 27 group 3, D71): `Harness.load("harness.toml")` or `Harness(...)`, `async
with`, `turn()` — three lines for a product that wants defaults, every port underneath what it
always was, and one step deeper without leaving it (`governance=`, `sink=`, `observer=`,
`agent=`; `.thread`, `.host` for the rest). `[budget]` is the file's word for the lease.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import anyio
import pytest

from shadow_hdk.kernel import Ceiling, Floor, Lease, Turn
from shadow_hdk.kernel.ports import AgentSession
from shadow_hdk.serve import Harness, load_settings
from shadow_hdk.serve.config import Budget
from tests.serve.test_serve_answers_a_host_in_any_language import ENFORCEABLE

pytestmark = pytest.mark.anyio


class TalkingProvider:
    """Thinks aloud, calls one tool, answers — so a turn has every kind of part."""

    def __init__(self) -> None:
        self.reach: Any = None

    async def open(self, *, tools: Any = (), workspace: Any = None, behaviour: Any = None) -> Any:
        provider = self

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                from shadow_hdk.runtime import current_run

                context = current_run()
                assert context is not None
                await context.activity("thinking", "hmm ")
                await provider.reach("list_dir", {"path": "."})
                await context.activity("text", "here")
                return Turn(text="the answer to " + prompt, reasoning="thought about it")

            async def close(self) -> None:
                pass

            async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
                raise NotImplementedError
                yield

        return cast(AgentSession, _Session())


def test_the_settings_read_a_budget_and_the_facade_says_it_as_a_lease(tmp_path: Path) -> None:
    (tmp_path / "harness.toml").write_text(
        '[environment]\nroot = "."\n[budget]\nsteps = 40\nseconds = 600\ncents = 50\n',
        encoding="utf-8",
    )
    settings = load_settings(tmp_path / "harness.toml")
    assert settings.budget == Budget(steps=40, seconds=600, cents=50)
    assert settings.budget.lease() == Lease(Ceiling(40, 600, 50), Floor(0))
    assert Budget().lease() == Lease(Ceiling(400, 3600, 500), Floor(0)), "the shipped default"
    (tmp_path / "harness.toml").write_text("[budget]\nmoney = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="money"):
        load_settings(tmp_path / "harness.toml")


async def test_three_lines_run_a_turn_and_yield_its_parts_in_order(tmp_path: Path) -> None:
    provider = TalkingProvider()
    (tmp_path / "harness.toml").write_text(
        f'[environment]\nroot = "ws"\nmode = "{ENFORCEABLE}"\n[budget]\nsteps = 30\n',
        encoding="utf-8",
    )
    kinds: list[str] = []
    with anyio.fail_after(60):
        async with Harness.load(tmp_path / "harness.toml", agent=cast(Any, provider)) as h:
            provider.reach = h.thread.registry.call
            async for part in h.turn("hello"):
                kinds.append(part.kind)
            said = h.thread.record.turns[-1].text
    assert said == "the answer to hello"
    assert kinds[0] == "started" and kinds[-1] == "turn", "events first, the turn's record last"
    assert "activity" in kinds, "what is happening, in order with the record (D63)"
    assert "item" in kinds, "the folded steps, runtime-side (D46)"
    assert kinds.index("activity") < kinds.index("turn")
    assert h.settings.root == (tmp_path / "ws").resolve()
    assert h.thread.remaining().ceiling.max_steps < 30, "the file's budget is the lease"


async def test_the_constructor_is_the_file_without_the_file(tmp_path: Path) -> None:
    provider = TalkingProvider()
    with anyio.fail_after(60):
        async with Harness(tmp_path / "ws", mode=ENFORCEABLE, agent=cast(Any, provider)) as h:
            provider.reach = h.thread.registry.call
            parts = [p async for p in h.turn("again")]
            assert parts[-1].kind == "turn" and parts[-1].turn is not None
            assert parts[-1].turn.text == "the answer to again"
            assert h.approvals is h.host.approvals, "the handles are the host's"
            assert h.modes and [m.id for m in await h.modes.all()][:3] == [
                "read-only",
                "workspace-write",
                "full",
            ]
            changed = await h.set_mode("full")
            assert [e.kind for e in changed] == ["mode_changed"]
    assert h.problems == (), "nothing was wanted that could not be had"


async def test_one_step_deeper_without_leaving_the_facade(tmp_path: Path) -> None:
    """A product with its own policy or record hands it in and keeps the rest."""
    from shadow_hdk.kernel import EffectProfile
    from shadow_hdk.kernel.ports import Allow, Context, Judgement, Refuse
    from shadow_hdk.runtime.testing import ListSink

    class NoListing:
        async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
            if context.attributes.get("component") == "list_dir":
                return Refuse("not in this house")
            return Allow()

    provider = TalkingProvider()
    ledger = ListSink()
    heard: list[str] = []

    class Hearing:
        async def on(self, event: Any) -> None:
            heard.append(event.kind)

        async def on_activity(self, activity: Any) -> None:
            heard.append("activity:" + activity.kind)

    with anyio.fail_after(60):
        async with Harness(
            tmp_path / "ws",
            mode=ENFORCEABLE,
            agent=cast(Any, provider),
            governance=NoListing(),
            sink=ledger,
            observer=Hearing(),
        ) as h:
            provider.reach = h.thread.registry.call
            parts = [p async for p in h.turn("go")]
    assert any(p.kind == "refused" for p in parts), "the product's policy judged"
    assert "activity:thinking" in heard and "started" in heard, "the product's observer heard"
    assert h.thread.record.turns[-1].text == "the answer to go"


async def test_a_battery_that_cannot_run_is_a_problem_the_facade_reports(tmp_path: Path) -> None:
    provider = TalkingProvider()
    with anyio.fail_after(60):
        async with Harness(
            tmp_path / "ws", mode=ENFORCEABLE, agent=cast(Any, provider), batteries=("nowhere",)
        ) as h:
            pass
    assert h.problems and "nowhere" in h.problems[0]


async def test_the_readme_three_lines_run_for_real(tmp_path: Path) -> None:
    """The README's `harness.toml` and Python snippet, run as printed — with the provider handed
    in, since a README cannot assume a subscription, and the file's root and mode this machine's."""
    import re

    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")
    toml_block = re.search(r"```toml\n# harness.toml\n(.*?)```", readme, re.S)
    py_block = re.search(
        r"```python\nfrom shadow_hdk.serve import Harness\n(.*?)```", readme, re.S
    )
    assert toml_block and py_block, "the README has the three lines and their file"
    toml = toml_block.group(1)
    toml = re.sub(r'mode = "workspace-write"', f'mode = "{ENFORCEABLE}"', toml)
    toml = re.sub(r'batteries = \["wigolo"\]', "batteries = []", toml)  # not installed here
    (tmp_path / "harness.toml").write_text(toml, encoding="utf-8")
    provider = TalkingProvider()
    snippet = py_block.group(1).replace(
        'Harness.load("harness.toml")', "Harness.load(path, agent=provider)"
    )
    printed: list[str] = []
    scope: dict[str, Any] = {
        "Harness": Harness,
        "path": tmp_path / "harness.toml",
        "provider": provider,
        "print": lambda *a: printed.append(" ".join(str(x) for x in a)),
    }
    # The snippet is a top-level `async with`; it becomes the body of one coroutine, verbatim.
    body = "\n".join("    " + line for line in snippet.rstrip("\n").split("\n"))
    exec(f"async def _snippet():\n{body}\n", scope)  # noqa: S102 — the README, run
    # The scripted provider calls tools through the thread's registry, which the three lines
    # never expose (a real provider reaches it over the socket): wire it once the thread opens.
    original_open = Harness.open

    async def open_and_wire(self: Harness) -> None:
        await original_open(self)
        provider.reach = self.thread.registry.call

    Harness.open = open_and_wire  # type: ignore[method-assign]
    try:
        with anyio.fail_after(60):
            await scope["_snippet"]()
    finally:
        Harness.open = original_open  # type: ignore[method-assign]
    assert printed[-1] == "the answer to add a .gitignore and run the tests"
    assert any(line.startswith("item list_dir") for line in printed), printed[:5]
    assert any(line.startswith("activity") for line in printed)
