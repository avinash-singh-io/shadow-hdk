"""The record speaks the industry's words (D61, `planning/the-substrate.md` §1.9).

`reasoned` is `reasoning`, `spent` is `usage`, `asked` is `approval_requested`, and a question the
agent asks the person is `input_requested` — the words Codex, Claude Code, OpenCode and the Agent
Client Protocol use, so a host reads the record without a glossary. What a host renders is an
`Item`; the kernel's plan unit stays a `Step`. `Lease`, the effect profile, the sink, provenance
and posture keep their names: they are ours, and nothing in the industry names them.
"""

from __future__ import annotations

from typing import get_args

from shadow_hdk.kernel import (
    ApprovalRequested,
    InputRequested,
    Reasoning,
    UsageReported,
)
from shadow_hdk.kernel.contracts import adapter_for
from shadow_hdk.kernel.events import Event
from shadow_hdk.kernel.observations import ApprovalRequest, InputRequest, Observation

INDUSTRY_KINDS = {
    "started",
    "composed",
    "invoked",
    "observed",
    "proposed",
    "refused",
    "approval_requested",
    "input_requested",
    "spawned",
    "held",
    "usage",
    "reasoning",
    "mode_changed",
    "ended",
}


def _kinds(union: object) -> set[str]:
    members = get_args(get_args(union)[0])
    return {m.__dataclass_fields__["kind"].default for m in members}


def test_the_event_kinds_are_the_industrys_words() -> None:
    assert _kinds(Event) == INDUSTRY_KINDS


def test_the_renamed_events_carry_what_they_did() -> None:
    reasoning = Reasoning(run_id="r", seq=1, at="t", step="s", text="because")
    usage = UsageReported(run_id="r", seq=2, at="t", step="s", usage=None)  # type: ignore[arg-type]
    asked = ApprovalRequested(
        run_id="r",
        seq=3,
        at="t",
        step="s",
        question="may it?",
        handle="h",
        component="run_shell",
        inputs={"command": "ls"},
    )
    input_ = InputRequested(run_id="r", seq=4, at="t", step="s", question="which one?", handle="h2")
    assert (reasoning.kind, usage.kind, asked.kind, input_.kind) == (
        "reasoning",
        "usage",
        "approval_requested",
        "input_requested",
    )
    assert asked.component == "run_shell" and asked.inputs == {"command": "ls"}


def test_the_observations_round_trip() -> None:
    for observation in (
        ApprovalRequest(question="may it?", handle="h", component="run_shell", inputs={"a": 1}),
        InputRequest(question="which one?", handle="h2"),
    ):
        adapter = adapter_for(Observation)
        assert adapter.validate_json(adapter.dump_json(observation)) == observation


def test_a_host_renders_items_and_the_kernel_plans_steps() -> None:
    from shadow_hdk.kernel import Step
    from shadow_hdk.runtime.items import Item, items, run_items

    assert Item.__name__ == "Item" and "Invoke" in str(Step)
    assert callable(items) and callable(run_items)
