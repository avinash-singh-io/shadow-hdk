---
type: Plan
status: complete
epic: production-boundary
---

# Phase 32 — One agent surface — Plan

```
# Execution:  G0 → (G1 ∥ G2) → G3 → G4 → G5
```

> **Derived, not brainstormed.**
> The group breakdown is the one thing the epic CANNOT know — it depends on
> code that exists now and did not when the epic was written. Everything
> above the groups is derived; the groups themselves are authored here.

Depends on: phase-31-a-host-knows-what-it-can-trust. Those must be complete before this starts.

Run policy: release: per-feature · push: per-phase · tdd: strict

---

## Group 0 — Lock one lifecycle evaluator *(sequential, blocks all)*

RED first with one parametrized product-facing scenario suite whose only variable is a scripted
CLI `AgentPort` or the not-yet-present model adapter. Lock the `Item.inputs` JSON shape, the stream
session's state machine and bearer-source precedence before implementation. Include adversarial
cases: a model emitting an unknown tool, usage omitted, two stream attachments, a cursor older than
the replay window, an insecure token file and a secret present in an error.

**Commit:** `test(runtime): lock the unified agent surface`

---

## Group 1 — A model is an agent below the thread *(parallel after G0)*

Implement `ModelAgent` as an `AgentPort` over the existing model/tool loop primitives. Its session
receives only the handed `ToolSource`, emits text/reasoning activity, reports honest usage and
supports the lifecycle the underlying model can actually provide. Wire model-provider resolution
into the same host candidate seam and carry the Phase 31 capability record; do not branch inside
`Thread` on provider kind.

**Commit:** `feat(agent): adapt models to the durable thread surface`

---

## Group 2 — The item says what was invoked *(parallel after G0)*

Carry the canonical inputs from `Invoked` into the pure item fold and every serialization path.
Define one payload boundary using the existing result-holding/redaction policy; clients receive the
same value or the same typed omission/handle. Regenerate JSON Schemas and TypeScript types, then
prove historical event streams still fold identically apart from the additive field.

**Commit:** `feat(items): retain invoked inputs across every surface`

---

## Group 3 — One reusable stream session *(after G1 and G2)*

Extract frame numbering, bounded outbox, attach/detach, cursor replay and grace expiry from
`wire/serve.py` into a runtime-level abstraction usable by an in-process product. Rebuild the wire
session on it and delete the private duplicate. Use an injected clock and no correctness sleeps;
the existing HTTP reconnect and second-stream refusal tests remain the integration proof.

**Commit:** `refactor(stream): share the durable session lifecycle`

---

## Group 4 — Silent links and safer bearer input *(after G3)*

Add heartbeat frames on idle live streams and a generated client's silence deadline/reattach path,
without writing heartbeats to events, items or checkpoints. Accept the serve bearer from an
environment variable or permission-checked file with explicit precedence; keep `--token` as a
documented local-only fallback. Refuse unreadable, over-permissive or ambiguous sources without
printing their contents.

**Commit:** `feat(serve): detect silence and keep bearers out of argv`

---

## Group 5 — Evidence and epic checkpoint *(sequential)*

Run the shared lifecycle evaluator against both provider kinds, wire reconnect tests, generated
client build, ruff, format, mypy strict, full pytest, document/schema invariants and benchmark.
Publish the additive Python migration and protocol/client behavior. Mark Phase 32 complete and
continue on the stacked Phase 33 branch; do not release before the epic gate.

**Commit:** `docs: record the unified agent surface`
