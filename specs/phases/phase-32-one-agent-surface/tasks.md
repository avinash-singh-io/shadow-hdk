---
type: Tasks
status: in-progress
epic: production-boundary
---
# Phase 32 — One agent surface — Tasks
> Mirrors `plan.md`. `[x]` done · `[/]` in-progress · `[ ]` todo.
> Verify before claiming done (Rule 12).
> **TDD strict:** no task may be marked `[x]` without a recorded red→green.
## Group 0 — Lock one lifecycle evaluator *(blocks)*
- [ ] RED: one scenario suite fails only on the missing model-agent path and missing shared fields/session contracts
- [ ] Lock item-input JSON/bounds, stream-session state transitions and bearer-source precedence/adversarial cases
- [ ] Verify focused evaluator tests fail for the intended missing behavior before implementation

## Group 1 — A model is an agent below the thread
- [ ] Implement `ModelAgent` over `ModelPort` and only its handed `ToolSource`
- [ ] Route API-model providers through the existing host candidate/capability-selection seam
- [ ] Verify model/CLI parity for turn, parking, holding, spend, cancellation, resume and activity

## Group 2 — The item says what was invoked
- [ ] Carry bounded canonical `Item.inputs` through the fold and Python contracts
- [ ] Carry the field through wire, schemas and generated TypeScript without client-side reconstruction
- [ ] Verify fold history, JSON round trips, schema drift and TypeScript compile

## Group 3 — One reusable stream session
- [ ] Extract monotone ids, bounded replay, single attachment, cursor and grace expiry behind an injected clock
- [ ] Make HTTP/SSE consume the shared session and remove the private duplicate
- [ ] Verify in-process state-machine/property tests and the existing D94 reconnect integrations

## Group 4 — Silent links and safer bearer input
- [ ] Add idle heartbeat frames and generated-client silence detection/reattach without durable record writes
- [ ] Add environment and permission-checked token-file sources with explicit precedence; retain the flag as local-only
- [ ] Verify heartbeat timing, silent-drop recovery, argv secrecy, permission refusal and log redaction

## Group 5 — Evidence and epic checkpoint
- [ ] Update architecture/package/migration docs with one agent and stream surface
- [ ] Run build, ruff check, format check, mypy strict, full pytest, parity/schema/client drift and benchmark
- [ ] Append phase evidence/history, mark Phase 32 complete and continue Phase 33 without releasing
