"""A composition becomes a LangGraph graph — the mapping `09` §10 states, and nothing more.

We do not interpret compositions; we compile them and let the engine run them (D12). What this
module owns is the *shape*: which nodes exist, how they are wired, and where the conditional edges
go. Execution, concurrency, checkpointing and interrupts are LangGraph's.

    Invoke / Await   one node calling the governed step
    Sequence         its children, wired in order
    FanOut           a dispatcher returning Sends, and a join
    Until            the body, plus a conditional edge on condition-or-count

Synthetic node names use ``__`` rather than ``:``: LangGraph reserves the colon for checkpoint
namespaces and refuses a node name containing one.

A composite nested inside another is **inlined** — more nodes and edges in the same graph. True
subgraphs, with their own checkpoint namespaces, arrive with sub-agents in Phase 6, which is the
first thing that needs them.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import JsonValue

from shadow_hdk.kernel.composition import (
    Await,
    Composition,
    Condition,
    FanOut,
    Invoke,
    Sequence,
    Step,
    StepId,
    Until,
)
from shadow_hdk.kernel.contracts import dump
from shadow_hdk.kernel.observations import Completed, Observation
from shadow_hdk.runtime.state import RunState
from shadow_hdk.runtime.step import StepExecutor

# ---------------------------------------------------------------- the plan


@dataclass(frozen=True)
class UntilPlan:
    """Everything the loop's conditional edge needs, decided once at plan time."""

    step_id: StepId
    body_entry: str
    body_exit: str
    done: str
    condition: Condition
    max_iterations: int
    watched: StepId
    """Whose output the condition is read from — the last step the body runs."""


@dataclass(frozen=True)
class Plan:
    """A composition's shape, with no executor in it — which is what makes it cacheable."""

    entry: str
    exit: str
    steps: Mapping[str, Step] = field(default_factory=dict)
    passthroughs: tuple[str, ...] = ()
    ticks: Mapping[str, StepId] = field(default_factory=dict)
    edges: tuple[tuple[str, str], ...] = ()
    fanouts: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    untils: tuple[UntilPlan, ...] = ()


class _Builder:
    def __init__(self) -> None:
        self.steps: dict[str, Step] = {}
        self.passthroughs: list[str] = []
        self.ticks: dict[str, StepId] = {}
        self.edges: list[tuple[str, str]] = []
        self.fanouts: dict[str, tuple[str, ...]] = {}
        self.untils: list[UntilPlan] = []

    def passthrough(self, name: str) -> str:
        self.passthroughs.append(name)
        return name

    def add(self, step: Step) -> tuple[str, str]:
        """Returns this step's (entry node, exit node). They differ only for composites."""
        match step:
            case Invoke() | Await():
                self.steps[step.id] = step
                return step.id, step.id
            case Sequence(id=seq_id, steps=children):
                if not children:
                    empty = self.passthrough(f"{seq_id}__empty")
                    return empty, empty
                first_entry, previous_exit = self.add(children[0])
                for child in children[1:]:
                    child_entry, child_exit = self.add(child)
                    self.edges.append((previous_exit, child_entry))
                    previous_exit = child_exit
                return first_entry, previous_exit
            case FanOut(id=fan_id, steps=children):
                dispatch = self.passthrough(f"{fan_id}__dispatch")
                join = self.passthrough(f"{fan_id}__join")
                entries = []
                for child in children:
                    child_entry, child_exit = self.add(child)
                    entries.append(child_entry)
                    self.edges.append((child_exit, join))
                self.fanouts[dispatch] = tuple(entries)
                if not entries:
                    self.edges.append((dispatch, join))
                return dispatch, join
            case Until(id=until_id, step=body, condition=condition, max_iterations=maximum):
                tick = f"{until_id}__tick"
                self.ticks[tick] = until_id
                done = self.passthrough(f"{until_id}__done")
                body_entry, body_exit = self.add(body)
                self.edges.append((tick, body_entry))
                self.untils.append(
                    UntilPlan(
                        step_id=until_id,
                        body_entry=tick,
                        body_exit=body_exit,
                        done=done,
                        condition=condition,
                        max_iterations=maximum,
                        watched=_last_step_id(body),
                    )
                )
                return tick, done
        raise TypeError(f"unknown step kind: {step!r}")  # pragma: no cover — the union is closed


def _last_step_id(step: Step) -> StepId:
    """Whose output an `Until` reads. The last thing the body actually invokes."""
    match step:
        case Invoke() | Await():
            return step.id
        case Sequence(steps=children) | FanOut(steps=children):
            return _last_step_id(children[-1]) if children else step.id
        case Until(step=body):
            return _last_step_id(body)
    return step.id  # pragma: no cover


def _build_plan(composition: Composition) -> Plan:
    builder = _Builder()
    root = Sequence("<root>", tuple(composition.steps))
    entry, exit_node = builder.add(root)
    return Plan(
        entry=entry,
        exit=exit_node,
        steps=dict(builder.steps),
        passthroughs=tuple(builder.passthroughs),
        ticks=dict(builder.ticks),
        edges=tuple(builder.edges),
        fanouts=dict(builder.fanouts),
        untils=tuple(builder.untils),
    )


_PLAN_CACHE: dict[bytes, Plan] = {}
_HITS = 0
_MISSES = 0


def plan_for(composition: Composition) -> Plan:
    """The same shape is planned once, however often an agent re-authors it (D11)."""
    global _HITS, _MISSES
    key = dump(composition, Composition).encode()
    cached = _PLAN_CACHE.get(key)
    if cached is not None:
        _HITS += 1
        return cached
    _MISSES += 1
    plan = _build_plan(composition)
    _PLAN_CACHE[key] = plan
    return plan


def plan_cache_stats() -> dict[str, int]:
    return {"hits": _HITS, "misses": _MISSES, "size": len(_PLAN_CACHE)}


# ---------------------------------------------------------------- the graph


def _output_of(observation: Observation) -> JsonValue:
    return observation.output if isinstance(observation, Completed) else None


def _reach(value: JsonValue, path: str) -> JsonValue:
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _step_node(step: Step, executor: StepExecutor) -> Callable[[RunState], Any]:
    async def node(state: RunState) -> dict[str, Any]:
        assert isinstance(step, Invoke | Await)
        observation = await executor.invoke(step, state)
        return {
            "handles": {step.id: _output_of(observation)},
            "observations": {step.id: observation},
        }

    return node


def _tick_node(step_id: StepId) -> Callable[[RunState], Any]:
    async def node(_state: RunState) -> dict[str, Any]:
        return {"iterations": {step_id: 1}}

    return node


async def _passthrough(_state: RunState) -> dict[str, Any]:
    return {}


def _send_to(children: tuple[str, ...]) -> Callable[[RunState], list[Send]]:
    def route(state: RunState) -> list[Send]:
        return [Send(child, state) for child in children]

    return route


def _until_route(plan: UntilPlan) -> Callable[[RunState], str]:
    def route(state: RunState) -> str:
        satisfied = _reach(state["handles"].get(plan.watched), plan.condition.path) == (
            plan.condition.equals
        )
        spent = state["iterations"].get(plan.step_id, 0)
        return plan.done if satisfied or spent >= plan.max_iterations else plan.body_entry

    return route


def compile_composition(
    composition: Composition, executor: StepExecutor, checkpointer: Any = None
) -> Any:
    """Build the graph. The plan is cached; binding the executor to it is cheap."""
    plan = plan_for(composition)
    graph: StateGraph = StateGraph(RunState)

    for name, step in plan.steps.items():
        graph.add_node(name, _step_node(step, executor))
    for name in plan.passthroughs:
        graph.add_node(name, _passthrough)
    for name, step_id in plan.ticks.items():
        graph.add_node(name, _tick_node(step_id))

    for source, target in plan.edges:
        graph.add_edge(source, target)
    for dispatch, children in plan.fanouts.items():
        graph.add_conditional_edges(dispatch, _send_to(children), list(children))
    for until in plan.untils:
        graph.add_conditional_edges(
            until.body_exit, _until_route(until), [until.body_entry, until.done]
        )

    graph.add_edge(START, plan.entry)
    graph.add_edge(plan.exit, END)
    return graph.compile(checkpointer=checkpointer)


__all__ = ["Plan", "compile_composition", "plan_cache_stats", "plan_for"]
