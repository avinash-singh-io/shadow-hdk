"""Each browser action is offered through ComponentPort and judged before reaching its engine."""

from typing import Any

from shadow_hdk.adapters.browser import BrowserComponents
from shadow_hdk.kernel import Binding, Ceiling, Completed, Composition, Ended, Floor, Invoke, Lease
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Allow, Ask, Context, Refuse
from shadow_hdk.runtime import Ports, RunOptions, resume, run
from shadow_hdk.runtime.testing import FixedClock, ListSink


class Engine:
    def __init__(self) -> None:
        self.calls: list[Any] = []
        self.closed: list[str] = []

    async def execute(self, action: str, inputs: Any, resource_scope: str) -> Any:
        self.calls.append((action, inputs, resource_scope))
        return Completed({"action": action})

    async def release_run(self, resource_scope: str) -> None:
        self.closed.append(resource_scope)


class ReadOnly:
    async def judge(self, effects: EffectProfile, context: Context) -> Any:
        return Refuse("read only") if effects.writes.names or effects.reaches else Allow()


async def test_read_only_allows_reading_and_images_but_refuses_interactions() -> None:
    engine = Engine()
    pack = BrowserComponents(engine=engine)
    registrations = await pack.registrations()
    reads = {r.id for r in registrations if not r.component.effects.writes.names}
    ports = Ports(components=(pack,), governance=ReadOnly(), sink=ListSink(), clock=FixedClock())
    events = [
        e
        async for e in run(
            Composition(
                tuple(
                    Invoke(
                        str(i),
                        r.id,
                        (Binding("selector", value="h1"),) if r.id == "browser_find" else (),
                    )
                    for i, r in enumerate(registrations)
                )
            ),
            ports,
            options=RunOptions(lease=Lease(Ceiling(40, 60, 0), Floor(0))),
        )
    ]
    assert reads == {
        "browser_snapshot",
        "browser_find",
        "browser_screenshot",
        "browser_tabs",
        "browser_console",
        "browser_requests",
        "browser_wait",
    }
    assert (
        {f"browser_{name}" for name, _, _ in engine.calls},
        [e.reason for e in events if e.kind == "refused"],
    ) == (
        reads,
        ["read only"] * (len(registrations) - len(reads)),
    )


async def test_ask_first_previews_the_value_and_does_not_dispatch_before_resume() -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    from shadow_hdk.runtime import InMemoryEffectJournal
    from shadow_hdk.runtime.testing import AllowAuthorizer, FixedAuthority

    class AskFirst:
        async def judge(self, effects: EffectProfile, context: Context) -> Ask:
            return Ask("type this value?")

    engine, pack = Engine(), None
    pack = BrowserComponents(engine=engine)
    ports = Ports(
        components=(pack,),
        governance=AskFirst(),
        sink=ListSink(),
        clock=FixedClock(),
        authority=FixedAuthority(),
        authorizer=AllowAuthorizer(),
        effect_journal=InMemoryEffectJournal(),
    )
    options = RunOptions(
        lease=Lease(Ceiling(10, 60, 0), Floor(0)),
        checkpointer=InMemorySaver(),
        run_id="approval-browser",
    )
    plan = Composition(
        (
            Invoke(
                "type",
                "browser_type",
                (
                    Binding("selector", value="#title"),
                    Binding("value", value="Reviewable value"),
                ),
            ),
        )
    )
    first = [e async for e in run(plan, ports, options=options)]
    questions = [e for e in first if e.kind == "approval_requested"]
    assert (engine.calls, [(q.component, q.inputs) for q in questions]) == (
        [],
        [("browser_type", {"selector": "#title", "value": "Reviewable value"})],
    )
    after = [e async for e in resume(plan, Allow(), ports, options=options)]
    assert isinstance(after[-1], Ended)
    assert (engine.calls, engine.closed, after[-1].reason) == (
        [("type", {"selector": "#title", "value": "Reviewable value"}, "approval-browser")],
        ["approval-browser"],
        "completed",
    )
