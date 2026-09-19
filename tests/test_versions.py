"""Every package moves together until 1.0 (D9).

Pre-1.0 the eighteen are one thing released eighteen ways: a contract change is a minor bump here
*and* a row on `intent-ecosystem/lanes/board.md` under *Pins*, because the join with the product
lane is the only place two lanes can break each other. *(It said **four** for nineteen phases, which
was true at Phase 0 and has been wrong since Phase 1 added adapters.)*

**A patch bump is not a contract change and takes no *Pins* row.** Every entry below until 0.13.1
was a minor, and each says what a host would have to change; 0.13.1 is the first that says nobody
has to change anything. One distribution since 0.27.0 (D78): one version, and the parts inside it
and a lockstep set with one member behind is a resolver error waiting to happen — but *moving
together* and *breaking the join* are different claims, and only the second belongs on the board.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "0.32.1"
"""0.32.1 — a patch (D9): `set_mode` and `add_root` during a running turn refuse with the typed
`TurnRunning` instead of closing the provider's session under the turn (BUG-056); no contract
change — the refusal kind already existed.

0.32.0 — tools as code, from any language (Phase 44): `thread/start {host_components}` carries a
host's components by inversion (D21) on the thread door; the TypeScript client gains `tool()`,
`components.serve`, a `Transport` and a stdio sidecar (`shadow-hdk-client/node`); the proof reads
stdout (BUG-057). Contract additions, protocol 3 unchanged — a minor (D9).

0.31.0 — plan admission (Epic 0009, Phase 36): a plan is admitted whole under limits that
narrow host → mode → parent; `plan_admitted`/`plan_refused` events; `compose` a component;
`thread/amend`, `plan_limits` and `unmapped_behaviour` on the wire, protocol 3 unchanged
(additive). A contract addition in the published shape — a minor (D9).

0.27.0 — one distribution (D78): `shadow-hdk`, with the specialised SDKs as extras
(`[langchain]`, `[mqtt]`, `[otel]`, `[sandbox]`, `[search]`, `[all]`), in place of eighteen
that moved together anyway. A consumer's install lines change, and the eighteen names never
ship — a contract change in the published shape.

0.26.1 — published: every package carries its URLs and classifiers for its PyPI page, and
the publish workflow builds, checks, publishes and smoke-installs the eighteen (no contract
change; a patch — D9).

0.26.0 — the packages proven as published artefacts: the providers wheel built for the first
time (BUG-035), every wheel built and looked into, a clean-venv install serving. The published
shape is what a consumer compiles against, so every package moves together (D9).

0.25.3 — a patch: the mode in settings is a mode id, `ask` included (BUG-034); `requires`
refuses an unknown environment name; the specs synced. No contract change (D9).

0.25.2 — a patch: one rule, one implementation (D77). `start_held` the one place a session
leader is started; `LineBuffer` the one framing; the root-name rule in place of a heuristic. No
contract change; every package moves together (D9).

0.25.1 — a patch: two fixes with no contract change. A battery's MCP server is a held session
leader ended with its group (BUG-033); Claude Code launched from a clean scope, no settings
sources and no auto-memory (ENH-012). Every package moves together (D9).

0.25.0 because the workspace, the modes and the wire grew (Phase 28, D73–D76): `Workspace`
and `Root` in the kernel; `ThreadRecord.roots` and `.environment`; `WorkspaceChanged`, the
fifteenth event kind; `AgentPort.open(resume=)`; `Environment.reopen`, `Environment(workspace=)`;
`ModeSpec.environment` and the fourth shipped mode, `ask`; `Thread.tools`, `Thread.add_root`,
`Thread.workspace`; on the wire `tools/list`, `skills/list`, `thread/add_root`, `roots` and
`environment` in the thread results, `root` in every `files/*` entry; `shadow-hdk-serve
[providers]`; `KeepingSink`; and a child run judged in its parent's context (BUG-030), which
changes what every host's policy is told. Additive on the surface and a change in what a
mode means underneath, so the join moves.

0.24.0 because the front door grew (Phase 27, D70–D72): `Harness`, `Part` and `Budget` in
`shadow-hdk-serve`; `Settings` grew `batteries`, `batteries_dir` and `budget`;
`ServeHost(governance=, sink=)`; `a_thread(agent=, batteries=, batteries_dir=)`;
`McpComponents(only=, aliases=, effects=)` — a widened adapter constructor; and the wire's
`batteries/list`. Additive all, but the wire is the contract a host compiles against and the
facade is what a product imports first, so the join moves.

0.23.0 because the wire's contract grew a second shape (Phase 26, D67–D69): `thread/*`,
`turn/*`, `approvals/*`, `run/cancel`, `store/*`, `modes/list`, `rules/list`, `files/*` as
methods; `activity`, `approval_request`, `input_request` and `request_withdrawn` as
notifications; `ThreadHost` a port the serving process implements; `thread/start` and
`thread/resume` results carry the root. A new package, `shadow-hdk-serve`, holds the shipped
composition and the console script, and pins the others by equality — an eighteenth distribution
in the lockstep set. Additive on the wire, but the wire is the contract a host in another language
compiles against (the TypeScript client is generated from it), so the join moves.

0.22.0 because the kernel grew the host's controls (Phase 25, D62–D66): `ThreadRecord` and
`TurnRecord` with the `ThreadStore` port; `Activity` beside the record; `Behaviour` and
`BehaviourArg` with `ModeChanged` a fourteenth event kind; `ActRule`; the `Store` port; and
`AgentPort.open` takes a `behaviour`. New contracts and one widened port, so a host that
implements `AgentPort` changes; the rest is additive — but additive on the kernel is still the
kernel, and the join moves.

0.21.0 because the record speaks the industry's words (D61): `reasoned` is `reasoning`, `spent`
is `usage`, `asked` is `approval_requested`, and `input_requested` is a thirteenth kind — the
agent's own question to the person. `Asked` the observation is `ApprovalRequest`; `InputRequest`
joins it. What a host renders is an `Item` (`runtime.items`); the handle it answers through is
`Approvals`, in the words `Approve`, `Deny`, `ApproveAndAddRule`; `RunContext.reasoned`/`ask` are
`reasoning`/`request_approval`; the wire's `step` notification is `item`. Renames, so every host
changes — once, to the words every product already uses.

0.20.0 because the kernel's `Asked` — the event and the observation — grew `component` and
`inputs` (D59): what a question is about, so the person answering can see what they are
consenting to. `Approvals.next_withdrawn` and `RunContext.ask(about=)` came with it, and the
wire's `context.ask` carries both. Additions all; a host reading `Asked` as before still can.

0.19.0 because the runtime's contract with a component grew two ways to ask (D57, D58):
`RunContext.keep`/`resumed` and a produced `Asked` observation that parks the run; `RunContext.ask`
and `Approvals` on `RunOptions` for a live question. `Dialect` grew `subtype_key`,
`mcp_config_shape`, `allow_override` and `failed_text_at` (Codex, measured). Nothing a host held
before changed shape; every one of these is an addition, and the wire's protocol grew three
messages for them. A host that answered questions at the top only keeps working as it did.

0.18.0 because the agent adapter's public surface grew: `Skill` has `description` and `source`
(D54) and `load_skill` refuses a file without a line, which a host's skill files may lack;
`SkillRegistry`, `SkillSource`, `DirectorySkills`, `MintedSkills`, `SkillComponents`, `kept_from`
and `shipped_skills` are new (D55, D56). No kernel type changed and `AgentComponent` is as it was,
so a host that never held a `Skill` changes nothing; one with skill files adds a line to each.

0.17.0 because a host's view of a run changed shape in two places and a host that served the
registry over a socket has to change one line. `Step` grew `parent` and `run_items` grew
`nested=` (D51's example found that a host waiting for the orchestrator's step rendered nothing
for the whole run); `serve_over_socket` yields `(port, token)` and the relay wants the token in
its environment (D52) — a caller holding the old `port` breaks at unpacking, which is the right
place to break. `Step.json` is republished; the wire's `STEP` carries the new field.

0.16.0 because three distributions are **gone** — `adapters-workspace`,
`adapters-sandbox-subprocess` and `adapters-contained` — and one, `adapters-environment`, stands
where they were (D48–D50). No
kernel type changed; a host that depended on any of the three has to change its imports, and
pre-1.0 that is a minor.

0.15.0 because the stream grew a **twelfth** kind, `Reasoning` — what the model thought, on the
record beside what it did (D45) — and `ModelResponse`, `ModelChunk` and `Turn` grew a `reasoning`
field to carry it there, each defaulting empty so an adapter that never heard of it produces a
response that reads as *did not say* rather than failing to construct. Both cross the wire.

0.14.0 because the kernel grew a **second provider seam** and the record that describes one
(D39, D40). `AgentPort` and `AgentSession` are what a provider owning its own loop satisfies —
messages do not go in and tool calls do not come back, because those leave through the injected
registry (D42) — and `Provider` is the published contract a host reads its provider library into.
A host that only ever held a `ModelPort` needs to change nothing; both are additions.

0.13.1 is a **patch**: nothing a host depends on moved. `served_over_http` stopped printing a
`CancelledError` traceback on a clean exit (BUG-017) — it cancelled uvicorn mid-`serve` instead of
asking it to stop and waiting, and no wire test could see it because pytest's anyio runner absorbs
an unretrieved exception. Everything else in the release is documentation. No *Pins* row.

0.13.0 because a stop signal is no longer an ordinary exception, and a sink that cannot write
ends the run rather than the step (TD-006). A host catching `Exception` around a component no
longer swallows a lease that ran out, a cancellation, or a port that broke — which is what it was
doing, because every component adapter catches `Exception` and D7 says it should.

0.12.0 because an `Ask` is answered with a `Judgement` and the answer now decides (D38,
BUG-010). A host that answers with a bare value gets a refusal where it used to get silent
success, because the re-run judgement — not the human — was deciding.

0.11.0 because `RunState` grew `children` — what a run is holding rides in the checkpoint, so a
parent that parks comes back holding it still (D37, BUG-015). Before it, the parent found an empty
hand and quietly spawned a second child while the first stayed parked forever.

0.10.0 because `Message` grew `tool_calls` — an assistant message carries the calls it made
(BUG-005). Every provider rejects a tool result whose call is in no preceding message, and every
test used `ScriptedModel`, which never looked. `ModelRequest` is a published contract, so this one
crosses the wire.

0.9.0 because `RunState` grew `spent` — what a run has spent rides in the checkpoint so it
survives a park (D33, BUG-004). A host reading graph state directly sees a new field; the event
stream is unchanged. Before it, a lease of three steps admitted five across an Ask.

0.8.0 because `Observed` grew `posture` — every observation carries the posture of the component
that produced it, stamped by the runtime (D30); default `controlled`, so nothing that read the
stream before needs to change.

0.7.0 because two contracts grew: `Provenance.signature`, the proof beside the claim that
`signed_by` had been making since Phase 0 without anything reading it, and `Acted`, the receipt of
a world-effect — foreign id, idempotency key, exit, grounds — as a sixth observation kind. Both are
D27. Before that:
0.6.0 because the stream grew an **eleventh** kind, `UsageReported` (then `Spent`) — what a step
cost, said out loud instead of left in an output dict by convention (D20) — and `Usage` moved
beneath both `ports` and `events`, which could not import each other. 0.5.0 was the tenth kind,
`Held` — a child parked instead of ending and
its parent is keeping it, which a host would otherwise have to infer from the *absence* of `Ended`,
and a child that died silently looks the same. 0.4.0 was `Ended.detail`; 0.3.0 was
`Provenance.posture`; 0.2.0 was `ModelPort.stream`. Each is a contract change, so every package
moves together (D9)."""


def _distribution() -> dict[str, str]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    return {str(project["name"]): str(project["version"])}


def test_the_distribution_is_at_the_expected_version() -> None:
    assert _distribution() == {"shadow-hdk": EXPECTED}


def test_the_linux_helper_moves_with_the_kit() -> None:
    """The `shadow-hdk-sandbox` crate and its `shadow-hdk-linux-sandbox` distribution (Epic 0010,
    D123) ship beside the kit and are pinned by it under a Linux marker: one number, three places
    — the crate, its `pyproject.toml`, the kit's dependency line — or a Linux install resolves a
    helper from a different release than the kit that invokes it."""
    crate = tomllib.loads((ROOT / "native" / "sandbox" / "Cargo.toml").read_text())
    helper = tomllib.loads((ROOT / "native" / "sandbox" / "pyproject.toml").read_text())
    kit = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert crate["package"]["name"] == "shadow-hdk-sandbox"
    assert crate["package"]["version"] == EXPECTED
    assert helper["project"]["name"] == "shadow-hdk-linux-sandbox"
    assert helper["project"]["version"] == EXPECTED
    pins = [d for d in kit["project"]["dependencies"] if d.startswith("shadow-hdk-linux-sandbox")]
    assert len(pins) == 1, kit["project"]["dependencies"]
    assert pins[0].startswith(f"shadow-hdk-linux-sandbox=={EXPECTED};")
    assert "sys_platform == 'linux'" in pins[0]
    assert "native/sandbox" in kit["tool"]["uv"]["workspace"]["members"]


def test_the_parts_every_phase_relies_on_are_still_here() -> None:
    """A subset, not an equality: each phase adds adapters, and a test that had to be edited every
    time one arrived would be edited without being read."""
    parts = {p.name for p in (ROOT / "src" / "shadow_hdk").iterdir() if p.is_dir()}
    adapters = {p.name for p in (ROOT / "src" / "shadow_hdk" / "adapters").iterdir() if p.is_dir()}
    assert {"kernel", "runtime", "wire", "providers", "serve", "adapters"} <= parts
    assert {
        "basic",
        "agent",
        "modes",
        "mcp",
        "recording",
        "environment",
        "jsonl",
        "acp",
    } <= adapters
