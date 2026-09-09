"""Composition — what "program" means (09 §5).

The agent authors a composition; the runtime executes it, judging every step's effects through the
governance port as it goes. A single tool call is a composition of one step. The grammar is a
floor, not a ceiling: a new step kind is a kernel addition with an ADR, the same discipline as a
new effect field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Literal

from pydantic import Field, JsonValue

from shadow_hdk.kernel.components import RegistrationId

StepId = str
Handle = str
"""A name for a live intermediate value held by the runtime, passed between steps without being
flattened into tokens (09 §6)."""


@dataclass(frozen=True)
class Binding:
    """One input: either a literal value or a reference to an earlier step's output by handle."""

    name: str
    ref: Handle | None = None
    value: JsonValue | None = None


@dataclass(frozen=True)
class Condition:
    """A total, non-looping test over the last observation's output: ``output[path] == equals``."""

    path: str
    equals: JsonValue


@dataclass(frozen=True)
class Invoke:
    id: StepId
    component: RegistrationId
    inputs: tuple[Binding, ...] = ()
    kind: Literal["invoke"] = "invoke"


@dataclass(frozen=True)
class Await:
    """Wait for something slow — a person, a job. Compiles to an interrupt."""

    id: StepId
    component: RegistrationId
    inputs: tuple[Binding, ...] = ()
    kind: Literal["await"] = "await"


@dataclass(frozen=True)
class Sequence:
    id: StepId
    steps: tuple[Step, ...] = ()
    kind: Literal["sequence"] = "sequence"


@dataclass(frozen=True)
class FanOut:
    id: StepId
    steps: tuple[Step, ...] = ()
    kind: Literal["fan_out"] = "fan_out"


@dataclass(frozen=True)
class Until:
    """Loop with a stop: repeat ``step`` until ``condition`` holds, at most ``max_iterations``."""

    id: StepId
    step: Step
    condition: Condition
    max_iterations: int
    kind: Literal["until"] = "until"


Step = Annotated[Invoke | Await | Sequence | FanOut | Until, Field(discriminator="kind")]


@dataclass(frozen=True)
class Composition:
    """A first-class value: visible while it runs, changeable mid-flight, emitted as an event."""

    steps: tuple[Step, ...] = field(default_factory=tuple)
