"""What the deployment **is** decides what the model can **see**.

The chain, end to end and through a real run rather than by reading a profile:

    SubprocessSandbox(contained=False)   a deployment with no real isolation, saying so
        ↓
    a mode whose ceiling requires containment
        ↓
    narrows() is False  →  governance refuses
        ↓
    RunContext.visible() does not list it  →  the model is never offered it

The agent always *has* the ability to run code. The deployment decides the permission, once,
honestly — and the model is not tempted by a tool it may not use.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.adapters.modes import Mode, ModeGovernance
from shadow_hdk.adapters.sandbox_subprocess import SubprocessSandbox
from shadow_hdk.adapters.workspace import WorkspaceComponents
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Floor,
    Invoke,
    Lease,
    Observation,
    Observed,
    ScopeSet,
)
from shadow_hdk.kernel.ports import Context
from shadow_hdk.runtime import Ports, RunOptions, current_run, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)

EVERYTHING = ScopeSet(everything=True)

#: A deployment that permits writing and reaching, and **requires containment** before code runs.
NEEDS_CONTAINMENT = Mode(
    "careful",
    ceiling=EffectProfile(
        reads=EVERYTHING,
        writes=ScopeSet.of("workspace"),
        reaches=True,
        reversible=False,
        contained=True,
        costs=True,
    ),
)

LOOKING = make_registration("what_can_i_see", effects=EffectProfile(reads=EVERYTHING))


def sandbox(root: Path, *, contained: bool) -> SubprocessSandbox:
    return SubprocessSandbox(root, contained=contained, at="2026-09-10T00:00:00+00:00")


async def what_the_model_would_see(root: Path, *, contained: bool, governed: bool) -> list[str]:
    """Run something that asks the run itself what it may see, and report the names."""
    seen: list[str] = []

    async def look(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        seen.extend(
            registration.component.interface.name for registration in await context.visible()
        )
        return Completed(None)

    asking = InMemoryComponents([(LOOKING, look)])
    ports = Ports(
        model=ScriptedModel(),
        components=(asking, sandbox(root, contained=contained), WorkspaceComponents(root)),
        governance=ModeGovernance({"careful": NEEDS_CONTAINMENT}, default="careful")
        if governed
        else AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    async for _event in run(
        Composition((Invoke("s1", LOOKING.id),)),
        ports,
        options=RunOptions(lease=Lease(Ceiling(10, 600, 100), Floor(0))),
    ):
        pass
    return seen


async def test_an_uncontained_sandbox_is_refused_by_a_mode_that_requires_containment(
    tmp_path: Path,
) -> None:
    profile = sandbox(tmp_path, contained=False).effects
    governance = ModeGovernance({"careful": NEEDS_CONTAINMENT}, default="careful")
    judgement = await governance.judge(profile, Context(run_id="r", step="s"))
    assert judgement.kind == "refuse"


async def test_a_contained_sandbox_is_allowed_by_the_same_mode(tmp_path: Path) -> None:
    """The other half. A check that refuses everything is not a check."""
    profile = sandbox(tmp_path, contained=True).effects
    governance = ModeGovernance({"careful": NEEDS_CONTAINMENT}, default="careful")
    judgement = await governance.judge(profile, Context(run_id="r", step="s"))
    assert judgement.kind == "allow"


async def test_the_model_is_never_offered_a_sandbox_the_deployment_cannot_contain(
    tmp_path: Path,
) -> None:
    """Absent, not refused at call time — proven through a real run, not by reading the profile."""
    visible = await what_the_model_would_see(tmp_path, contained=False, governed=True)
    assert "run_python" not in visible
    assert "run_shell" not in visible
    assert "write_file" in visible, "the mode still permits writing; only code is out"


async def test_the_same_sandbox_on_a_contained_deployment_is_offered(tmp_path: Path) -> None:
    visible = await what_the_model_would_see(tmp_path, contained=True, governed=True)
    assert {"run_python", "run_shell"} <= set(visible)


async def test_without_a_mode_nothing_is_hidden(tmp_path: Path) -> None:
    """Allow-all is not a policy, and the test says so: with no mode the uncontained sandbox is
    offered. Hiding it is governance's doing, not the adapter's."""
    visible = await what_the_model_would_see(tmp_path, contained=False, governed=False)
    assert {"run_python", "run_shell"} <= set(visible)


async def test_an_agent_writes_a_note_and_a_page_that_exist_afterwards() -> None:
    """What all of this is *for*: the agent makes things, and they are on disk when it is done."""
    from shadow_hdk.adapters.agent import AgentComponent, Pattern

    from shadow_hdk.kernel.ports import ModelResponse, ToolCall

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        agent = AgentComponent(
            pattern=Pattern("writer", "Write what you are asked to."),
            effects=EffectProfile(reads=EVERYTHING, writes=ScopeSet.of("workspace"), costs=True),
            name="writer",
            at="2026-09-10T00:00:00+00:00",
        )
        model = ScriptedModel(
            [
                ModelResponse(
                    tool_calls=(
                        ToolCall(
                            id="w1",
                            name="write_file",
                            arguments={"path": "notes.md", "content": "# Lathe\n12 kg\n"},
                        ),
                        ToolCall(
                            id="w2",
                            name="write_file",
                            arguments={
                                "path": "out/page.html",
                                "content": "<h1>LATHE-3</h1>",
                            },
                        ),
                    )
                ),
                ModelResponse(
                    tool_calls=(ToolCall(id="d1", name="done", arguments={"summary": "written"}),)
                ),
            ]
        )
        ports = Ports(
            model=model,
            components=(WorkspaceComponents(root, at="2026-09-10T00:00:00+00:00"), agent),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        )
        events = [
            e
            async for e in run(
                Composition((Invoke("w", "writer", (Binding("brief", value="write them"),)),)),
                ports,
                options=RunOptions(lease=Lease(Ceiling(20, 600, 100), Floor(0))),
            )
        ]

        assert (root / "notes.md").read_text() == "# Lathe\n12 kg\n"
        assert (root / "out" / "page.html").read_text() == "<h1>LATHE-3</h1>"
        written = [e for e in events if isinstance(e, Observed) and e.step in {"w1", "w2"}]
        assert len(written) == 2
        assert all(isinstance(e.observation, Completed) for e in written)
