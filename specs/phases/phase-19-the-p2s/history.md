---
type: History
phase: 19-the-p2s
---

# Phase 19 — history

### [NOTE] 2026-09-10 — Group 1: 57% of the runtime's overhead was Pydantic building the same schema again
Topics: latency, d11, contracts, pydantic, bug-016
Affects-phases: none
Affects-specs: specs/backlog/backlog.md

Measured before anything changed:

```
a 100-step run built 101 TypeAdapters — 1.01 per step
   100 x Annotated[Completed | Refused | Asked | Failed | Pending | Acted, ...]
     1 x Composition
building TypeAdapter(Observation) costs 0.743 ms each
101 of them is about 75 ms of a 132 ms run (57%)
```

Constructing a `TypeAdapter` walks the whole annotation and builds a core schema. It is a **pure
function of the type**. `contracts.py` built a fresh one on every `dump`, `load`, `round_trip` and
`json_schema`, and D19 — *a checkpoint is a wire* — means every step of every run dumps its
observation through there.

One dict, keyed on the type. Measured after, three runs: **59.4 / 60.0 / 59.7 ms — 0.594 ms/step**,
against D11's ≤ 1 ms and the 1.36 it had drifted to. The drift was entirely this, and the 57.0 ms
the benchmark recorded at founding was the true cost of the design all along.

**The cache is unbounded on purpose and it is not TD-005's kind of growth.** The key is a *type*, and
a program holds finitely many — they come from module import, not from traffic. Evicting here would
discard exactly the object that is expensive to rebuild, from a set that cannot grow with load.

---

### [DECISION] 2026-09-10 — a stopwatch cannot guard a stopwatch budget
Topics: latency, testing, d11, ci
Affects-phases: none
Affects-specs: specs/architecture/decisions.md

D11's benchmark asserts at **three times** its targets, and its docstring explains why: a shared
runner is not the development machine, so a tighter assertion would flake, and *a flaky gate is
worse than no gate, because it teaches you to ignore it*. That reasoning is sound and it is also
why a 2.4× regression sat in the runtime for phases without a single red build.

The obvious response is to tighten the slack. **It does not work, and the numbers say so.** The
runner measured **3.93 ms/step** where this machine measured **1.36** — about three times. Any
assertion tight enough to catch a 2.4× drift is inside the range that hardware alone explains. The
two overlap, so no threshold separates *the code got slower* from *the machine is slower*.

So the gate keeps its slack and stops being the thing relied on. What guards this class of
regression is a claim about the **mechanism**, which is the same on every machine and cannot flake:
`tests/kernel/test_an_adapter_is_built_once_per_type.py` asserts that a run builds **one** adapter
per contract type however many steps it takes. It would have failed on the first step of the commit
that introduced this, on any hardware, in milliseconds.

*Why:* a performance budget is a claim about work done, and work done is countable. Timing it is a
proxy that a shared runner makes unusable at exactly the resolution that matters.

*Overturned by:* dedicated hardware for the benchmark, which would make a stopwatch meaningful
again — and would still not be as good as counting.

---

### [NOTE] 2026-09-10 — BUG-013 reproduced, and the audit's row is right about the bug and wrong about the place
Topics: derivation, canonical, unicode, floats
Affects-phases: none
Affects-specs: none

Measured before anything is written, so Group 2 starts from facts:

```
1. the evaluator raises past invoke:
   Infinity        -> *** RAISED InvalidOperation
   1e22            -> *** RAISED InvalidOperation
   mul 1e15 x 1e15 -> *** RAISED InvalidOperation
   NaN literal     -> completed
2. the fingerprint is not canonical:
   lit "1" / "1.0" / "1.00" -> three different fingerprints
3. NFC vs NFD:
   in a *unit*  -> same fingerprint          (the row's claim, not reproduced here)
   in a *cell*  -> NFC counts 1, NFD counts 0 (a wrong answer, not merely a different hash)
4. cell types pass through unchecked:
   1 vs "1" -> different fingerprints
   0.1 as a float and "0.1" as a string both sum to 0.300000000000
```

Three corrections to the row, all in the direction of it being **more** serious in one place and
less in another. **Unicode normalisation is a cell problem, not a unit problem** — and it is not a
fingerprint problem at all there, it is a *wrong count*: the same word in two normal forms is two
different values, so `count_where` answers 1 or 0 depending on how the text was typed. **A `NaN`
literal does not raise**, where three other literals do. And **float cells do not corrupt the
arithmetic** the way the row implies — `0.1` and `"0.1"` sum identically, because the value goes
through `str()` — but they do produce a **different fingerprint**, so the damage is to identity and
re-derivation rather than to the number.

---

### [NOTE] 2026-09-10 — the first green CI run in this repository's history
Topics: ci, latency, d11
Affects-phases: none
Affects-specs: none

`phase-19-the-p2s`, run 34504668539. **All checks passed** — the first time that has ever happened
here, two runs after the trigger was widened and the first one went red.

```
Required test coverage of 90% reached. Total coverage: 96.77%
842 passed, 10 deselected
  100 sequential steps: 123.9 ms (1.239 ms/step, best of 9)
  50-way fan-out:        49.0 ms (best of 9)
  100 steps in 10 nested subgraphs: 131.4 ms (1.314 ms/step, best of 9)
```

Against the same three numbers on the same runner before the adapter cache — **392.7 ms, 176.6 ms
and 403.1 ms** — all three of which were red.

It also settles the ratio the previous decision rests on. The runner does **1.239 ms/step** where
this machine does **0.594**: about **2.1×**, measured rather than assumed. The regression it failed
to catch was **2.4×**. Those two numbers are close enough to touch, which is the whole argument for
counting adapters instead of timing steps.

---
