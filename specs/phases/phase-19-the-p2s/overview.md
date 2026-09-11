---
type: Phase
phase: 19
name: the-p2s
epic: 0008-what-the-audit-found
status: complete
topics: [audit, latency, derivation, sink, contracts, growth, d11]
deps: [phase-18-the-p1s]
---

# Phase 19 — The P2s

Phases 17 and 18 closed every P0 and P1 the audit filed. What is left of it is the P2s, and one new
row that the audit could not have found because nothing was running the code anywhere but here.

The rule does not change: **every row is reproduced before it is fixed**, and a row whose fix is not
mine to choose is recorded as such rather than invented.

## The row that was not in the audit

**BUG-016 — the runtime is over D11's latency budget.** Found on 2026-09-10 by the first CI run in
this repository's history, minutes after Phase 18 widened the trigger that had kept CI from ever
seeing a phase commit.

The benchmark had recorded **57.0 ms (0.570 ms/step)** for a hundred sequential steps. Measured
again after Phase 18: **135.9, 136.9 and 136.4 ms — 1.36 ms/step**, against D11's budget of ≤ 1 ms.
The gate never went red because its assertion sits at three times the target, which the benchmark's
own docstring says catches an order of magnitude rather than a drift — and a drift is exactly what
happened. The same docstring says *the printed numbers are the real signal; read them*, and through
five groups of Phase 18 nobody did, including me.

## What was measured before anything was written

```
1. a 100-step run built 101 TypeAdapters — 1.01 per step
      100 x Annotated[Completed | Refused | Asked | Failed | Pending | Acted, ...]
        1 x Composition
2. building TypeAdapter(Observation) costs 0.743 ms each
   101 of them is about 75 ms of a 132 ms run (57%)
```

**Fifty-seven per cent of the runtime's per-step overhead is Pydantic building the same schema
again.** `kernel/contracts.py` constructs a fresh `TypeAdapter` on every `dump`, `load`,
`round_trip` and `json_schema` call, and D19 — *a checkpoint is a wire* — means every step dumps its
observation through it. The adapter is a pure function of the type; nothing about it is per-call.

That is a satisfying number to find and a slightly embarrassing one to have shipped, and both halves
belong in the record: the design was right, the budget was right, the gate was too loose to notice,
and the printed line that would have said so was printed on every CI run that never happened.

## What this phase does not decide

**TD-007** touches D30 and R9 — posture, the act state machine, and who may declare what. ADR-1 is
the owner's and is not written. Whatever part of TD-007 turns out to be policy is recorded and left;
whatever part is plumbing is built.

**The ADRs themselves** (ADR-1, ADR-2) are the owner's. TD-008 asks that the constitutional
documents describe the same day, which is not the same thing and is mine.
