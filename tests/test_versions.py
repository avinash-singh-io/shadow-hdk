"""Every package moves together until 1.0 (D9).

Pre-1.0 the seventeen are one thing released seventeen ways: a contract change is a minor bump here
*and* a row on `intent-ecosystem/lanes/board.md` under *Pins*, because the join with the product
lane is the only place two lanes can break each other. *(It said **four** for nineteen phases, which
was true at Phase 0 and has been wrong since Phase 1 added adapters.)*

**A patch bump is not a contract change and takes no *Pins* row.** Every entry below until 0.13.1
was a minor, and each says what a host would have to change; 0.13.1 is the first that says nobody
has to change anything. The packages still move together, because they pin each other by equality
and a lockstep set with one member behind is a resolver error waiting to happen — but *moving
together* and *breaking the join* are different claims, and only the second belongs on the board.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "0.14.0"
"""0.14.0 because the kernel grew a **second provider seam** and the record that describes one
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
0.6.0 because the stream grew an **eleventh** kind, `Spent` — what a step cost, said out loud
instead of left in an output dict by convention (D20) — and `Usage` moved beneath both `ports` and
`events`, which could not import each other. 0.5.0 was the tenth kind, `Held` — a child parked
instead of ending and
its parent is keeping it, which a host would otherwise have to infer from the *absence* of `Ended`,
and a child that died silently looks the same. 0.4.0 was `Ended.detail`; 0.3.0 was
`Provenance.posture`; 0.2.0 was `ModelPort.stream`. Each is a contract change, so every package
moves together (D9)."""


def _packages() -> dict[str, str]:
    found = {}
    for pyproject in sorted(ROOT.glob("packages/**/pyproject.toml")):
        project = tomllib.loads(pyproject.read_text())["project"]
        found[project["name"]] = project["version"]
    return found


def test_every_package_is_at_the_same_version() -> None:
    versions = _packages()
    assert versions, "the version walk found no packages"
    assert set(versions.values()) == {EXPECTED}, versions


def test_the_packages_every_phase_relies_on_are_still_here() -> None:
    """A subset, not an equality: each phase adds adapters, and a test that had to be edited every
    time one arrived would be edited without being read."""
    assert {
        "shadow-hdk-kernel",
        "shadow-hdk",
        "shadow-hdk-adapters-basic",
        "shadow-hdk-adapters-agent",
    } <= set(_packages())
