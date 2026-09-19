"""A web read from the serving process, under the shipped modes (ENH-038, D138).

The `ddgs` battery vouches `web_search` `reaches = true, contained = false` — true: the read runs
in the serving process, outside any sandbox. The shipped policies judge it as they judge anything:
`read-only` allows it (look, and look at the web — the documented design; a read-only policy has
to work over any environment, and it writes nothing that a reach could carry out); `workspace-write`
hides it (the silent writing mode; a reach beside writes is an egress channel); `ask` **asks**
before it since 0.34 — "every write, run or delete inside the workspace is asked about" is its
definition, and Claude Code's default prompts before a fetch — and an `allow` rule for the one
tool stands in for the person. That row is the door a served product uses. The battery's file is
unchanged; nothing re-vouches an effect to get past a ceiling.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.adapters.modes import ActRules, ModeGovernance, ModeRegistry, shipped_modes
from shadow_hdk.kernel import EffectProfile, ScopeSet
from shadow_hdk.kernel.ports import Allow, Ask, Context, Refuse
from shadow_hdk.kernel.rules import ActRule

pytestmark = pytest.mark.anyio

ROOT = Path(__file__).resolve().parents[3]

WEB_READ = EffectProfile(reads=ScopeSet.of("web"), reaches=True, contained=False)
"""What the search battery declares: a reach from the process, nothing written."""
CONTAINED_REACH = EffectProfile(reads=ScopeSet.of("web"), reaches=True, contained=True)
"""The same read through something that contains it — a proxied fetch (D137), a boxed command."""
A_WRITE = EffectProfile(writes=ScopeSet.of("workspace"))


def ctx(mode: str) -> Context:
    """What the runtime puts on a judgement (D82): the mode, and the act's component."""
    return Context(
        run_id="r",
        step="tools__web_search",
        principal="p",
        attributes={"mode": mode, "component": "web_search", "inputs": {"query": "lathe"}},
    )


def governance(rules: ActRules | None = None) -> ModeGovernance:
    return ModeGovernance(ModeRegistry(shipped_modes()), default="ask", rules=rules)


async def test_the_silent_writing_mode_refuses_an_uncontained_reach() -> None:
    judged = await governance().judge(WEB_READ, ctx("workspace-write"))
    assert isinstance(judged, Refuse), judged


async def test_read_only_reads_the_web_as_it_reads_anything() -> None:
    """The documented design, kept: a read that writes nothing, over any environment."""
    judged = await governance().judge(WEB_READ, ctx("read-only"))
    assert isinstance(judged, Allow), judged


@pytest.mark.parametrize("mode", ["read-only", "workspace-write", "ask"])
async def test_a_contained_reach_is_not_the_question(mode: str) -> None:
    judged = await governance().judge(CONTAINED_REACH, ctx(mode))
    assert isinstance(judged, Allow), judged


async def test_ask_asks_before_an_uncontained_reach_and_an_allow_rule_stands_in() -> None:
    """The door: `ask` puts the reach to the person — and "approve and add a rule" makes the one
    tool standing (D65), so a product that wants search without a prompt writes one row."""
    asked = await governance().judge(WEB_READ, ctx("ask"))
    assert isinstance(asked, Ask), asked

    standing = ActRules([ActRule(component="web_search", decision="allow", mode="ask")])
    allowed = await governance(standing).judge(WEB_READ, ctx("ask"))
    assert isinstance(allowed, Allow), allowed

    # A rule never widens a ceiling: the same row does nothing under workspace-write.
    still = await governance(standing).judge(WEB_READ, ctx("workspace-write"))
    assert isinstance(still, Refuse), still


async def test_ask_still_asks_before_a_write_and_full_allows_the_reach() -> None:
    assert isinstance(await governance().judge(A_WRITE, ctx("ask")), Ask)
    assert isinstance(await governance().judge(WEB_READ, ctx("full")), Allow)


def test_the_shipped_ceilings_say_so() -> None:
    by_id = {spec.id: spec.policy for spec in shipped_modes()}
    assert by_id["read-only"].ceiling.contained is False, "look, and look at the web"
    assert by_id["workspace-write"].ceiling.contained is True
    assert by_id["ask"].ceiling.contained is False
    assert by_id["ask"].ask_above is not None and by_id["ask"].ask_above.contained is True
    assert by_id["full"].ceiling.contained is False


def test_the_search_battery_still_says_what_is_true() -> None:
    battery = (ROOT / "src/shadow_hdk/serve/batteries_library/ddgs.toml").read_text()
    assert "effects = { reaches = true, contained = false }" in battery
