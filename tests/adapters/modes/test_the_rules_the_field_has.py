"""The rules the field has (Phase 29 group 6, D85).

Claude Code's permission rules read in one order — deny, then ask, then the mode, then allow —
and its ask and deny rules hold in every mode, `bypassPermissions` included. Ours read the same
way now: a matching `deny` refuses in `full`; a matching `ask` puts the call to the person in
`full`; an `allow` still only stands in for the person where the mode would have asked — a rule
never widens a ceiling. And a rule's inputs may be patterns: `"path": "finance/**"`, matched
against the path as the tool receives it — relative to the primary root, or `name/…` for another.
"""

from __future__ import annotations

import pytest

from shadow_hdk.adapters.modes import ActRules, ModeGovernance, ModeRegistry, shipped_modes
from shadow_hdk.kernel import ActRule, EffectProfile, ScopeSet
from shadow_hdk.kernel.ports import Allow, Ask, Context, Refuse

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
WRITES_INSIDE = EffectProfile(reads=WORKSPACE, writes=WORKSPACE, reversible=False)
READS = EffectProfile(reads=WORKSPACE)


def _context(mode: str, component: str = "write_file", **inputs: str) -> Context:
    return Context(
        run_id="r",
        step="s",
        attributes={"mode": mode, "component": component, "inputs": dict(inputs)},
    )


def _governance(*rules: ActRule) -> ModeGovernance:
    return ModeGovernance(
        ModeRegistry(shipped_modes()), default="workspace-write", rules=ActRules(rules)
    )


# ---------------------------------------------------------------- patterns


def test_a_rules_inputs_may_be_patterns_anchored_to_a_root() -> None:
    rule = ActRule(component="write_file", inputs={"path": "finance/**"})
    assert rule.matches("write_file", {"path": "finance/revenue.csv"})
    assert rule.matches("write_file", {"path": "finance/q3/notes.md"})
    assert not rule.matches("write_file", {"path": "sales/finance.csv"})
    assert not rule.matches("write_file", {"path": "finances/x"})
    other_root = ActRule(component="write_file", inputs={"path": "second/*.md"})
    assert other_root.matches("write_file", {"path": "second/NOTES.md"})
    assert not other_root.matches("write_file", {"path": "second/deep/NOTES.md"})
    assert not other_root.matches("write_file", {"path": "NOTES.md"})
    # What always held: exact, and a trailing `*` as a prefix.
    assert ActRule(component="w", inputs={"path": "a.txt"}).matches("w", {"path": "a.txt"})
    assert not ActRule(component="w", inputs={"path": "a.txt"}).matches("w", {"path": "a.txt2"})
    assert ActRule(component="w", inputs={"path": "notes/*"}).matches("w", {"path": "notes/a/b"})
    assert ActRule(component="run_shell", inputs={"command": "git *"}).matches(
        "run_shell", {"command": "git status"}
    )
    assert not ActRule(component="run_shell", inputs={"command": "git *"}).matches(
        "run_shell", {"command": "rm -rf /"}
    )


# ---------------------------------------------------------------- deny and ask hold everywhere


@pytest.mark.parametrize("mode", ["read-only", "ask", "workspace-write", "full"])
async def test_a_deny_rule_holds_in_every_mode(mode: str) -> None:
    governance = _governance(ActRule(component="write_file", decision="deny"))
    judged = await governance.judge(WRITES_INSIDE, _context(mode, path="a.txt"))
    assert isinstance(judged, Refuse), (mode, judged)
    assert "rule" in judged.reason


@pytest.mark.parametrize("mode", ["ask", "workspace-write", "full"])
async def test_an_ask_rule_holds_in_every_mode_that_would_have_allowed(mode: str) -> None:
    governance = _governance(
        ActRule(component="write_file", inputs={"path": "finance/**"}, decision="ask")
    )
    asked = await governance.judge(WRITES_INSIDE, _context(mode, path="finance/revenue.csv"))
    assert isinstance(asked, Ask), (mode, asked)
    assert "rule" in asked.question
    elsewhere = await governance.judge(WRITES_INSIDE, _context(mode, path="sales/notes.md"))
    if mode == "ask":
        assert isinstance(elsewhere, Ask), "the mode itself asks"
    else:
        assert isinstance(elsewhere, Allow), (mode, elsewhere)


async def test_deny_is_read_before_ask_and_a_rule_never_widens_the_ceiling() -> None:
    governance = _governance(
        ActRule(component="write_file", decision="ask"),
        ActRule(component="write_file", decision="deny", inputs={"path": "secrets/**"}),
    )
    assert isinstance(
        await governance.judge(WRITES_INSIDE, _context("full", path="secrets/key")), Refuse
    )
    assert isinstance(await governance.judge(WRITES_INSIDE, _context("full", path="a.txt")), Ask)
    # `read-only` refuses a write by its ceiling; an allow rule does not make it a write mode.
    allowing = _governance(ActRule(component="write_file", decision="allow"))
    refused = await allowing.judge(WRITES_INSIDE, _context("read-only", path="a.txt"))
    assert isinstance(refused, Refuse) and "does not permit" in refused.reason


async def test_an_allow_rule_still_stands_in_for_the_person_where_the_mode_asks() -> None:
    governance = _governance(ActRule(component="write_file", inputs={"path": "notes/*"}))
    assert isinstance(
        await governance.judge(WRITES_INSIDE, _context("ask", path="notes/today.md")), Allow
    )
    assert isinstance(await governance.judge(WRITES_INSIDE, _context("ask", path="a.txt")), Ask)


async def test_a_reads_only_act_can_be_denied_too() -> None:
    """A deny rule is not about the ask line: a read a product forbids is refused below it."""
    governance = _governance(
        ActRule(component="read_file", decision="deny", inputs={"path": ".env*"})
    )
    assert isinstance(
        await governance.judge(READS, _context("full", "read_file", path=".env.local")), Refuse
    )
    assert isinstance(
        await governance.judge(READS, _context("full", "read_file", path="README.md")), Allow
    )
