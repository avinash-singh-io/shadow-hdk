"""A behaviour — who the model should be — becomes that CLI's flags, as data (D64).

A mode carries a `Behaviour`: a system prompt, a model, an effort, a temperature, which tools it
is offered. A provider file maps each field to the flag that CLI takes (`behaviour_args`), the
way the dialect already maps the transport (D40). A field the CLI has no flag for is **reported**,
never dropped — a behaviour a host set and the provider silently ignored is worse than a refusal.
"""

from __future__ import annotations

from typing import Any

import pytest

from shadow_hdk.adapters.jsonl.transport import argv_for, unmapped_behaviour
from shadow_hdk.kernel import Behaviour, Dialect, Provider
from shadow_hdk.kernel.providers import BehaviourArg

pytestmark = pytest.mark.anyio

CLAUDE_BEHAVIOUR_ARGS = (
    BehaviourArg(field="system", flag="--system-prompt"),
    BehaviourArg(field="append_system", flag="--append-system-prompt"),
    BehaviourArg(field="model", flag="--model"),
    BehaviourArg(field="effort", flag="--effort"),
)


def a_provider(**dialect_fields: Any) -> Provider:
    return Provider(
        id="fake",
        kind="agent",
        bin="fake-cli",
        transport="jsonl",
        launch_args=("-p",),
        dialect=Dialect(behaviour_args=CLAUDE_BEHAVIOUR_ARGS, **dialect_fields),
    )


def test_each_mapped_field_becomes_its_flag() -> None:
    behaviour = Behaviour(system="You are an analyst.", model="claude-opus-5", effort="high")
    argv = argv_for(a_provider(), tools=(), behaviour=behaviour)

    assert argv[:1] == ["-p"]
    assert (
        "--system-prompt" in argv
        and argv[argv.index("--system-prompt") + 1] == "You are an analyst."
    )
    assert argv[argv.index("--model") + 1] == "claude-opus-5"
    assert argv[argv.index("--effort") + 1] == "high"
    assert "--append-system-prompt" not in argv, "an unset field adds no flag"


def test_a_field_the_provider_cannot_map_is_reported_never_dropped() -> None:
    behaviour = Behaviour(model="claude-opus-5", temperature=0.2)
    # the provider maps model but has no flag for temperature
    unmapped = unmapped_behaviour(a_provider(), behaviour)

    assert unmapped == ["temperature"], "a set field with no flag must be named, not silently lost"
    argv = argv_for(a_provider(), tools=(), behaviour=behaviour)
    assert "--model" in argv and "0.2" not in argv


def test_no_behaviour_is_no_flags() -> None:
    assert argv_for(a_provider(), tools=()) == ["-p"]
    assert unmapped_behaviour(a_provider(), None) == []


def test_the_shipped_claude_code_file_maps_the_measured_flags() -> None:
    from shadow_hdk.providers import shipped

    dialect = shipped()["claude-code"].dialect
    assert dialect is not None
    by_field = {a.field: a.flag for a in dialect.behaviour_args}
    assert by_field["system"] == "--system-prompt"
    assert by_field["append_system"] == "--append-system-prompt"
    assert by_field["model"] == "--model"
    assert by_field["effort"] == "--effort"


# ---------------------------------------------------------------- a flag that takes key=value


def test_a_templated_flag_renders_the_value_into_its_argument() -> None:
    """Codex takes reasoning effort as a config override — `-c model_reasoning_effort="high"` —
    not as a flag of its own. A `template` on the mapping says how the value is spelled after the
    flag (D64, ENH-028); `{value}` is where it goes."""
    provider = Provider(
        id="fake",
        kind="agent",
        bin="fake-cli",
        transport="jsonl",
        dialect=Dialect(
            behaviour_args=(
                BehaviourArg(field="model", flag="-m"),
                BehaviourArg(
                    field="effort", flag="-c", template='model_reasoning_effort="{value}"'
                ),
            )
        ),
    )
    argv = argv_for(provider, tools=(), behaviour=Behaviour(model="gpt-5", effort="low"))
    assert argv[argv.index("-m") + 1] == "gpt-5"
    assert argv[argv.index("-c") + 1] == 'model_reasoning_effort="low"'


def test_the_shipped_codex_file_maps_model_and_effort_and_names_the_rest() -> None:
    from shadow_hdk.providers import shipped

    codex = shipped()["codex"]
    behaviour = Behaviour(system="be brief", model="gpt-5", effort="low", temperature=0.1)
    argv = argv_for(codex, tools=(), behaviour=behaviour)
    assert argv[argv.index("-m") + 1] == "gpt-5"
    assert argv[argv.index("-c") + 1] == 'model_reasoning_effort="low"'
    assert unmapped_behaviour(codex, behaviour) == ["system", "temperature"]
