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

A composite nested inside another is a **subgraph** with its own checkpoint namespace, which is
what lets a branch be cancelled and a child be resumed where it slept (Phase 6, D15). It was inlined
at first — more nodes and edges in one graph — and this paragraph went on saying so for six phases
after that stopped being true (TD-008).
"""

from __future__ import annotations

import json
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

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
from shadow_hdk.runtime.state import MARKS, SUMS, RunState
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
    subgraphs: Mapping[str, Plan] = field(default_factory=dict)
    """A nested composite, planned in its own right and added to this graph as one node. The node
    is named for the composite, which is what gives the scope a checkpoint namespace."""


class DuplicateStepId(ValueError):
    """Two steps in one composition share an id.

    Not a style rule. `RunState.handles` is one flat dict keyed by step id, and that flatness is
    what lets a `Binding` reach an earlier sibling in an outer scope — so ids cannot be scoped
    apart, and a repeat is an error. Before this was caught, two steps sharing an id collapsed into
    **one node with a self-edge**, and the run looped until its lease was gone.
    """

    def __init__(self, step_id: StepId) -> None:
        super().__init__(f"two steps share the id {step_id!r}; step ids are unique per composition")
        self.step_id = step_id


class _Builder:
    def __init__(self, seen: set[StepId] | None = None) -> None:
        self.steps: dict[str, Step] = {}
        self.passthroughs: list[str] = []
        self.ticks: dict[str, StepId] = {}
        self.edges: list[tuple[str, str]] = []
        self.fanouts: dict[str, tuple[str, ...]] = {}
        self.untils: list[UntilPlan] = []
        self.subgraphs: dict[str, Plan] = {}
        # Shared with every nested builder: an id repeated in another *scope* is still a repeat.
        self.seen: set[StepId] = seen if seen is not None else set()

    def claim(self, step_id: StepId) -> StepId:
        if step_id in self.seen:
            raise DuplicateStepId(step_id)
        self.seen.add(step_id)
        return step_id

    def nest(self, composite: Step) -> tuple[str, str]:
        """A composite inside another becomes its own plan, added to this graph as one node."""
        name = self.claim(composite.id)
        inner = _Builder(self.seen)
        entry, exit_node = inner.add(composite, top=True)
        self.subgraphs[name] = inner.finish(entry, exit_node)
        return name, name

    def finish(self, entry: str, exit_node: str) -> Plan:
        return Plan(
            entry=entry,
            exit=exit_node,
            steps=dict(self.steps),
            passthroughs=tuple(self.passthroughs),
            ticks=dict(self.ticks),
            edges=tuple(self.edges),
            fanouts=dict(self.fanouts),
            untils=tuple(self.untils),
            subgraphs=dict(self.subgraphs),
        )

    def passthrough(self, name: str) -> str:
        self.passthroughs.append(name)
        return name

    def add(self, step: Step, *, top: bool = False) -> tuple[str, str]:
        """Returns this step's (entry node, exit node). They differ only for composites.

        `top` marks the one composite this builder is *for* — the root sequence, or the composite a
        nested builder was made to plan. Any other composite is nested, and becomes a subgraph.
        """
        if not top and isinstance(step, Sequence | FanOut | Until):
            return self.nest(step)
        match step:
            case Invoke() | Await():
                self.steps[self.claim(step.id)] = step
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
    entry, exit_node = builder.add(root, top=True)
    return builder.finish(entry, exit_node)


PLAN_CACHE_MAX = 512
"""How many distinct shapes are kept (TD-005).

**Bounded because the key set grows with traffic.** It is the full JSON of a composition, and a
model authors a new one on most turns — measured, 2000 distinct compositions gave 2000 entries and
about 6.3 MiB that nothing ever released. That is the opposite of `contracts.adapter_for`, whose key
is a *type*: a program holds finitely many of those and they come from module import, so bounding
there would discard the expensive object from a set that cannot grow.

**Safe here for a reason that does not generalise.** A plan is pure — no executor in it, which is
what made it cacheable at all — so an evicted one costs exactly a rebuild. Five hundred and twelve
is far past any single agent's repertoire of shapes and still a bound; a knob was rejected because a
host cannot tell what to set it to and a wrong setting is worse than this one.
"""

_PLAN_CACHE: OrderedDict[bytes, Plan] = OrderedDict()
_HITS = 0
_MISSES = 0
_EVICTED = 0


def plan_for(composition: Composition) -> Plan:
    """The same shape is planned once, however often an agent re-authors it (D11).

    **Least recently used**, not oldest inserted: a loop alternating between two shapes must keep
    both, and evicting by age of insertion would drop the one it is about to need next.
    """
    global _HITS, _MISSES, _EVICTED
    key = dump(composition, Composition).encode()
    cached = _PLAN_CACHE.get(key)
    if cached is not None:
        _HITS += 1
        _PLAN_CACHE.move_to_end(key)
        return cached
    _MISSES += 1
    plan = _build_plan(composition)
    _PLAN_CACHE[key] = plan
    while len(_PLAN_CACHE) > PLAN_CACHE_MAX:
        _PLAN_CACHE.popitem(last=False)
        _EVICTED += 1
    return plan


def plan_cache_stats() -> dict[str, int]:
    """`evicted` is not decoration: a cache that silently forgets is one nobody can size, and the
    count is the only way to tell a bound being *hit* from a bound being merely *set*."""
    return {"hits": _HITS, "misses": _MISSES, "size": len(_PLAN_CACHE), "evicted": _EVICTED}


# ---------------------------------------------------------------- the graph


def _output_of(observation: Observation) -> JsonValue:
    return observation.output if isinstance(observation, Completed) else None


def _reach(value: JsonValue, path: str) -> JsonValue:
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


class Node(Protocol):
    """What a graph node is to LangGraph: called with the state — by that name, which a bare
    `Callable[[RunState], ...]` cannot promise — and answering the update to fold in."""

    def __call__(self, state: RunState) -> Awaitable[dict[str, Any]]: ...


def _step_node(step: Step, executor: StepExecutor) -> Node:
    async def node(state: RunState) -> dict[str, Any]:
        assert isinstance(step, Invoke | Await)
        before = executor.spent()
        observation = await executor.invoke(step, state)
        after = executor.spent()
        return {
            "handles": {step.id: _output_of(observation)},
            # Plain JSON on the way into the state (D19) — a checkpointer is a boundary, and our
            # class names are not something a host should have to name in its serializer.
            "observations": {step.id: json.loads(dump(observation, Observation))},
            # What the run holds after this step, so a park does not lose it (D37).
            "children": executor.holding(),
            # What *this step* added, so the reducer can sum across a fan-out's branches (D33).
            "spent": {
                **{name: after[name] - before[name] for name in SUMS},
                **{name: after[name] for name in MARKS},
            },
        }

    return node


def _tick_node(step_id: StepId) -> Node:
    async def node(state: RunState) -> dict[str, Any]:
        return {"iterations": {step_id: 1}}

    return node


async def _passthrough(state: RunState) -> dict[str, Any]:
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


def _graph_from(plan: Plan, executor: StepExecutor, checkpointer: Any = None) -> Any:
    graph = StateGraph(RunState)

    for name, step in plan.steps.items():
        graph.add_node(name, _step_node(step, executor))
    for name in plan.passthroughs:
        graph.add_node(name, _passthrough)
    for name, step_id in plan.ticks.items():
        graph.add_node(name, _tick_node(step_id))
    for name, nested in plan.subgraphs.items():
        # No checkpointer of its own: LangGraph gives a subgraph the parent's, under a namespace
        # named for this node. Handing it a second one would give the scope two records.
        graph.add_node(name, _graph_from(nested, executor))

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


def compile_composition(
    composition: Composition, executor: StepExecutor, checkpointer: Any = None
) -> Any:
    """Build the graph. The plan is cached; binding the executor to it is cheap."""
    return _graph_from(plan_for(composition), executor, checkpointer)


__all__ = [
    "PLAN_CACHE_MAX",
    "DuplicateStepId",
    "Plan",
    "compile_composition",
    "plan_cache_stats",
    "plan_for",
]
