---
type: Plan
phase: 19-the-p2s
---

# Phase 19 — plan

```
# Sequential. The red gate first, then the correctness rows, then the debts.
```

## Group 1 — the latency budget (BUG-016)

- reproduce: count the `TypeAdapter`s a run builds and price one
- cache the adapter per type in `kernel/contracts.py`; it is a pure function of the type
- **RED as a claim about the mechanism, not a wall-clock number** — a stopwatch assertion is the
  thing that failed here, and asserting one harder would be repeating the mistake. What is asserted
  is *a run builds one adapter per contract type, not one per step*
- re-measure, and decide on the evidence whether D11's assertion can be tightened

## Group 2 — derivation and the sink (BUG-013, BUG-014)

- the evaluator's raise, the fingerprint's canonical form, floats at the edge
- `FileSink`: the short write, and a torn tail followed by an append
- **check Phase 14's two equivalent mutants before rebuilding them** — `fsync` is per-inode and a
  torn line can only be the last; if that reasoning still holds it is cited, not re-derived

## Group 3 — the shared shape and what bounds growth (TD-004, TD-005)

- the contract suites reach seven of fourteen adapters; the other seven are the ones nothing holds
- the plan cache keyed on full JSON and never evicting; the emitter, wire and witness queues

## Group 4 — the leaks and the record (TD-006, TD-007, TD-008)

- governance and port handling outside the governed step
- posture's self-declared default — build the plumbing, record the policy as the owner's
- the constitutional documents made to describe one day; the ADR directory

## Not in this phase, and why

- **ENH-002** TLS on `MqttLink` — no TLS broker on this machine
- **ENH-003** a protocol-adapter contract suite — waits on a second protocol adapter, deliberately
- **ADR-1, ADR-2** — the owner's
