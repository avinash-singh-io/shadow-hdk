"""A skill says what it needs, and is told no before it starts (D17).

`10` §306: a skill is *a team-authored procedure, a file in a registry, declaring which components
it needs **so skill and mode can be checked against each other***. The check is the point, so it
runs before the first turn — against `RunContext.visible()`, which is the same computation the model
sees, so a skill cannot be told it may use something the model would never be offered.

Checking lazily, when the skill first calls a tool, was rejected: it spends a model turn learning
what a file could have said, and the failure lands three steps into the work rather than as a
refusal to start.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from shadow_hdk.adapters.agent import Skill, load_skill, missing_for
from shadow_hdk.adapters.modes import Mode, ModeGovernance
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Completed,
    Composition,
    EffectProfile,
    Invoke,
    Observation,
    Registration,
    ScopeSet,
)
from shadow_hdk.kernel.ports import GovernancePort
from shadow_hdk.runtime import Ports, RunOptions, current_run, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)

EVERYTHING = ScopeSet(everything=True)
WORKSPACE = ScopeSet.of("workspace")

READ = make_registration("read_file", effects=EffectProfile(reads=WORKSPACE))
WRITE = make_registration("write_file", effects=EffectProfile(writes=WORKSPACE, reversible=False))
DRIVER = make_registration("driver", effects=EffectProfile())

TIDY_UP = """
name = "tidy-up"
description = "Put a file's contents back where they belong, saying what moved and why."
needs = ["read_file", "write_file"]
prompt = \"\"\"
Read the file, decide what is out of place, and put it back where it belongs.
Say what you moved and why before you move it.
\"\"\"
"""


def _skill_file(tmp_path: Path, body: str = TIDY_UP) -> Path:
    written = tmp_path / "tidy-up.toml"
    written.write_text(body.strip() + "\n")
    return written


def test_a_skill_is_a_file_that_says_what_it_needs(tmp_path: Path) -> None:
    skill = load_skill(_skill_file(tmp_path))
    assert skill.name == "tidy-up"
    assert skill.needs == frozenset({"read_file", "write_file"})
    assert "out of place" in skill.prompt


@pytest.mark.parametrize(
    ("body", "says"),
    [
        ('name = "x"\nprompt = "p"\nneeds = ["a"]\nextra = 1\n', "extra"),
        ('prompt = "p"\n', "name"),
        ('name = "x"\n', "prompt"),
        ('name = "x"\nprompt = "p"\n', "description"),
    ],
    ids=["unknown key", "no name", "no prompt", "no line"],
)
def test_a_bad_skill_file_is_refused_by_name(tmp_path: Path, body: str, says: str) -> None:
    written = tmp_path / "bad.toml"
    written.write_text(body)
    with pytest.raises(ValueError) as refused:
        load_skill(written)
    message = str(refused.value)
    assert says in message and "bad.toml" in message, message


def test_a_skill_needing_nothing_is_always_allowed() -> None:
    assert missing_for(Skill(name="think", prompt="Think about it."), []) == frozenset()


async def _visible_under(governance: GovernancePort) -> list[Registration]:
    """What a run can actually see under a governance — the same call the model's catalogue uses."""
    seen: list[list[Registration]] = []

    async def look(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        seen.append(list(await context.visible()))
        return Completed(None)

    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(READ, _ok), (WRITE, _ok), (DRIVER, look)]),),
        governance=governance,
        sink=ListSink(),
        clock=FixedClock(),
    )
    from shadow_hdk.kernel import Ceiling, Floor, Lease

    async for _ in run(
        Composition((Invoke("s1", DRIVER.id),)),
        ports,
        options=RunOptions(lease=Lease(Ceiling(10, 600, 100), Floor(0))),
    ):
        pass
    assert seen, "the driver never ran"
    return seen[0]


async def _ok(_inputs: JsonValue) -> Observation:
    return Completed("ok")


def _mode(effects: EffectProfile) -> ModeGovernance:
    one = Mode("only", effects)
    return ModeGovernance({one.name: one}, default=one.name)


async def test_a_skill_whose_needs_are_all_visible_is_allowed(tmp_path: Path) -> None:
    skill = load_skill(_skill_file(tmp_path))
    visible = await _visible_under(
        _mode(
            EffectProfile(
                reads=EVERYTHING, writes=EVERYTHING, reversible=False, contained=False, costs=True
            )
        )
    )
    assert missing_for(skill, visible) == frozenset()


async def test_a_skill_needing_what_the_mode_hides_is_refused_and_says_which(
    tmp_path: Path,
) -> None:
    """The whole of `10` §306. A reading mode hides the irreversible write, so the skill is told no
    **before the first turn**, naming what is missing rather than failing three steps in."""
    skill = load_skill(_skill_file(tmp_path))
    visible = await _visible_under(
        _mode(EffectProfile(reads=EVERYTHING, contained=False, costs=True))
    )
    missing = missing_for(skill, visible)
    assert missing == frozenset({"write_file"}), missing
    assert "read_file" not in missing, "the check hid something the mode allows"


async def test_a_skill_names_a_component_the_way_a_composition_does(tmp_path: Path) -> None:
    """By **registration id**, not by interface name.

    An adapter may register `search` under the id `brave:search`, and only the id is what
    `Invoke.component` takes. Matching the interface name too would let a skill declare a need it
    could not then invoke — a check that says yes to something the runtime will not resolve.
    """
    prefixed = make_registration("search", registration_id="brave:search")
    by_id = Skill(name="find", prompt="Find it.", needs=frozenset({"brave:search"}))
    by_interface = Skill(name="find", prompt="Find it.", needs=frozenset({"search"}))
    assert missing_for(by_id, [prefixed]) == frozenset()
    assert missing_for(by_interface, [prefixed]) == frozenset({"search"})
