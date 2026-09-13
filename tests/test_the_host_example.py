"""The host example consumes the runtime in-process: its own policy, record and store handed in,
the projection rendered, the brain chosen. Nothing here costs a subscription — the scripted brain
is the proof, and the two live brains are chosen the same way.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from examples.host.brains import AT, WORKER, Brain, scripted
from examples.host.host import Outcome, host
from examples.host.policy import Policy

from shadow_hdk.adapters.agent import AgentComponent
from shadow_hdk.adapters.environment import local_sandbox
from shadow_hdk.kernel import (
    Allow,
    Ask,
    Binding,
    Composition,
    Context,
    EffectProfile,
    Invoke,
    Refuse,
    ScopeSet,
)
from shadow_hdk.kernel.ports import ModelResponse, ToolCall, Usage
from shadow_hdk.runtime.testing import ScriptedModel

pytestmark = pytest.mark.anyio

EVERYTHING = ScopeSet(everything=True)


def a_brain_that_only_looks(brief: str, *, writes: ScopeSet) -> Brain:
    """Looks, proposes what it saw, stops. Declares `writes` so a test can choose whether the
    policy has a question to ask at the top."""
    script = [
        ModelResponse(
            tool_calls=(ToolCall(id="l1", name="list_dir", arguments={"path": "."}),),
            usage=Usage(10, 2, 1),
            reasoning="Let me look.",
        ),
        ModelResponse(
            tool_calls=(
                ToolCall(
                    id="l2",
                    name="propose",
                    arguments={"kind": "finding", "payload": {"saw": "the workspace"}},
                ),
            ),
            usage=Usage(10, 2, 1),
        ),
        ModelResponse(
            tool_calls=(ToolCall(id="l3", name="done", arguments={"summary": "looked"}),),
            usage=Usage(10, 2, 1),
        ),
    ]
    worker = AgentComponent(
        pattern=WORKER,
        effects=EffectProfile(reads=EVERYTHING, writes=writes, costs=True),
        name="worker",
        at=AT,
    )
    plan = Composition((Invoke("worker", "worker", (Binding("brief", value=brief),)),))
    return Brain(model=ScriptedModel(script), components=(worker,), plan=plan, called="scripted")


# ---------------------------------------------------------------- the policy is over effects


async def test_the_policy_judges_effects_and_never_a_name() -> None:
    policy = Policy()
    where = Context(run_id="r", step="s")

    assert isinstance(await policy.judge(EffectProfile(reads=EVERYTHING), where), Allow)
    assert isinstance(
        await policy.judge(EffectProfile(writes=ScopeSet.of("workspace")), where), Allow
    )
    outside = await policy.judge(EffectProfile(writes=ScopeSet.of("workspace", "home")), where)
    assert isinstance(outside, Ask) and "home" in outside.question
    everything = await policy.judge(EffectProfile(writes=EVERYTHING), where)
    assert isinstance(everything, Ask) and "everything" in everything.question
    assert isinstance(await policy.judge(EffectProfile(reaches=True), where), Refuse)
    assert isinstance(
        await Policy(allow_network=True).judge(EffectProfile(reaches=True), where), Allow
    )


# ---------------------------------------------------------------- the ledger keeps proposals


async def test_the_ledger_is_the_hosts_record_and_says_so_as_json(tmp_path: Path) -> None:
    outcome = await host(
        "look",
        root=tmp_path / "ws",
        brain=a_brain_that_only_looks("look", writes=ScopeSet.of("workspace")),
        store=tmp_path / "runs.sqlite",
        mode="full",
        on_line=lambda _l: None,
    )

    assert outcome.ended == "completed"
    assert [p.kind for p in outcome.ledger.proposals] == ["finding"]
    assert '"saw": "the workspace"' in outcome.ledger.as_json()


# ---------------------------------------------------------------- the projection is rendered live


async def test_steps_are_rendered_as_they_close_with_reasoning_first(tmp_path: Path) -> None:
    lines: list[str] = []
    await host(
        "look",
        root=tmp_path / "ws",
        brain=a_brain_that_only_looks("look", writes=ScopeSet.of("workspace")),
        store=tmp_path / "runs.sqlite",
        mode="full",
        on_line=lines.append,
    )
    plain = [strip(line) for line in lines]

    thought = next(i for i, line in enumerate(plain) if line.startswith("∴ Let me look"))
    listed = next(i for i, line in enumerate(plain) if line.startswith("  ✓ list_dir"))
    worker = next(i for i, line in enumerate(plain) if line.startswith("✓ worker"))
    assert thought < listed < worker, plain
    assert any("¢" in line for line in plain), "the spend was not rendered"


def strip(line: str) -> str:
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", line)


# ------------------------------------------------------- a question parks the run in the store


async def test_an_unanswered_question_parks_the_run_and_a_later_call_resumes_it(
    tmp_path: Path,
) -> None:
    """The host answers questions; a host that cannot answer now leaves the run in its store and
    the *next* call — a new saver over the same file — finishes it. The runtime holds nothing."""
    brain = a_brain_that_only_looks("look", writes=EVERYTHING)
    store = tmp_path / "runs.sqlite"

    parked: Outcome = await host(
        "look", root=tmp_path / "ws", brain=brain, store=store, mode="full", on_line=lambda _l: None
    )
    assert parked.question is not None and "outside the workspace" in parked.question
    assert parked.ended is None, "a parked run must not report Ended"
    assert store.exists() and store.stat().st_size > 0

    lines: list[str] = []
    finished = await host(
        "look",
        root=tmp_path / "ws",
        brain=a_brain_that_only_looks("look", writes=EVERYTHING),
        store=store,
        mode="full",
        on_line=lines.append,
        run_id=parked.run_id,
        resume_with=Allow(),
    )
    assert finished.ended == "completed", [strip(line) for line in lines]
    assert any(strip(line).startswith("  ✓ list_dir") for line in lines)


async def test_a_refusal_ends_the_run_without_the_work(tmp_path: Path) -> None:
    brain = a_brain_that_only_looks("look", writes=EVERYTHING)
    outcome = await host(
        "look",
        root=tmp_path / "ws",
        brain=brain,
        store=tmp_path / "runs.sqlite",
        mode="full",
        on_line=lambda _l: None,
        answer=lambda _q: Refuse("not today"),
    )
    assert outcome.question is None
    assert outcome.ended == "completed"
    assert not [
        e
        for e in outcome.events
        if e.kind == "invoked" and getattr(e, "component", "") == "list_dir"
    ]
    # The host's "no" is the step's observation — a `Refused` answered where the step was.
    answered = [e for e in outcome.events if e.kind == "observed" and e.step == "worker"]
    assert [getattr(e.observation, "reason", None) for e in answered] == ["not today"]


# --------------------------------------------------- inside the environment, when there is one


@pytest.mark.skipif(local_sandbox() is None, reason="no OS sandbox on this machine")
async def test_inside_the_workspace_a_write_is_confined_and_nobody_is_asked(tmp_path: Path) -> None:
    asked: list[str] = []

    def answer(question: str) -> Allow:
        asked.append(question)
        return Allow()

    outcome = await host(
        "take notes",
        root=tmp_path / "ws",
        brain=scripted("take notes"),
        store=tmp_path / "runs.sqlite",
        mode="workspace-write",
        on_line=lambda _l: None,
        answer=answer,
    )
    assert outcome.ended == "completed"
    assert asked == [], "a confined write is inside the workspace; the policy had nothing to ask"
    assert (tmp_path / "ws" / "NOTES.md").exists()


# ------------------------------------------------------- skills: chosen, minted, kept by the host


async def test_the_worker_chooses_a_shipped_skill_and_mints_one_the_ledger_keeps(
    tmp_path: Path,
) -> None:
    """Self-evolution as a governed act: the worker mints a procedure, the sink receives it as a
    proposal, and the *host* — its ledger — decides to keep it. The runtime kept nothing."""
    first = await host(
        "take notes",
        root=tmp_path / "ws",
        brain=scripted("take notes"),
        store=tmp_path / "runs.sqlite",
        mode="full",
        on_line=lambda _l: None,
        answer=lambda _q: Allow(),
    )
    # Choosing a skill is a step on the record, like any other act (D55).
    chosen = [
        e
        for e in first.events
        if e.kind == "invoked" and getattr(e, "component", "") == "use_skill"
    ]
    assert [getattr(e, "inputs", None) for e in chosen] == [{"name": "look-before-you-change"}]
    minted = [p.payload for p in first.ledger.proposals if p.kind == "skill"]
    assert [p["name"] for p in minted if isinstance(p, dict)] == ["notes-first"]

    # The next run is handed the ledger as a source; the minted skill is back, labelled kept.
    again = scripted("take notes", kept=first.ledger)
    assert again.skills is not None
    names = {s.name: s.source for s in await again.skills.all()}
    assert names["notes-first"] == "kept"
    assert names["look-before-you-change"] == "shipped"
