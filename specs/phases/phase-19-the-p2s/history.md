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

### [NOTE] 2026-09-10 — Group 2: a canonicaliser that returns its input is not canonicalising
Topics: derivation, canonical, testing, bug-013
Affects-phases: none
Affects-specs: none

Two existing tests failed when the fingerprint was made canonical, and both were right to. Each
asserted `to_tree(parse(x)) == x` — that the canonical tree echoes the caller's own spelling back.

That is a **weaker property than canonical**, and it is precisely what let `"1"`, `"1.0"` and
`"1.00"` carry three identities for one quantity. `to_tree` lives under a section heading that says
*canonical*, and a canonicaliser that returns its input unchanged is not doing the job its heading
claims. The tests were not wrong about something small; they had pinned the bug in place.

What they hold now is what a caller actually depends on: **a ground survives the round trip** —
store the tree, parse it back, get the same ground, unit and all — and **the tree is a fixed
point**, so one pass canonicalises and further passes change nothing, which is what makes it usable
as an identity. The unit claim moved into a test of its own, because it is not about spelling and
would otherwise have been carried by a test that no longer says anything about it.

The component's test asserted the claim carries *the caller's* ground; it carries the canonical one,
so that two callers who wrote the same comparison differently record one thing.

---

### [DECISION] 2026-09-10 — a cell is a string or a boolean, and a number arrives as text
Topics: derivation, exactness, d26, bug-013
Affects-phases: none
Affects-specs: none

`Table.rows` has been annotated `Mapping[str, str | bool]` since Phase 12 and nothing enforced it,
so a JSON number went straight through. **Refused rather than coerced.**

The measured damage was narrower than the audit implied and still decisive. The arithmetic survived:
`0.1` as a JSON number and `"0.1"` as a string both sum to `0.300000000000`, because the value goes
through `str()` and Python's shortest-repr round-trips the double faithfully. What did not survive
was the **fingerprint** — two identical tables had two identities, so the damage is to re-derivation
rather than to the number.

Coercing would have fixed the fingerprint and left the deeper thing wrong. A JSON number has already
been through a float by the time this engine sees it, so accepting one means the exactness D26
promises started from a value somebody else had already rounded. **A string is the only JSON form
that carries a decimal intact**, and a boolean carries itself — which is why `str | bool` was the
right annotation and only ever needed enforcing.

The refusal names the row index, the column and what to send instead, quoted the way JSON quotes,
because a caller writing JSON cannot send what Python's `repr` shows them.

Rejected: coercing `int` but refusing `float`, which is defensible and leaves callers guessing which
of two JSON numbers is acceptable; and accepting both with a canonical fingerprint, which makes the
identity trustworthy while leaving the inputs not.

*Overturned by:* a caller with a real corpus of integer cells and no ability to quote them, which
would be an argument for a documented coercion rather than for silence.

**Units are still string equality with no cancellation, and that is deliberate.** Whether `kg·m/s²`
cancels is a question about what this engine's unit system *is*, not a defect in what it does today;
nothing in the backlog asks for it, and inventing an algebra here would be inventing a contract.

---

### [NOTE] 2026-09-10 — Group 2: an equivalence that was true until the process restarted
Topics: sink, durability, mutation, bug-014
Affects-phases: none
Affects-specs: none

Phase 14 named two mutants equivalent in `FileSink` and gave reasons: `fsync` is per-inode, and **a
torn line can only be the last**. The first still holds. The second is false, and the way it is
false is worth keeping.

It holds within one process's lifetime — a torn line is what a crash mid-write leaves, and nothing
after it is written. But **a restart opens the same file `O_APPEND` and writes onto the end of it**,
which puts a torn line in the middle. And a restart is the only time a torn line exists at all, so
the assumption failed in exactly the case the reasoning was about.

Measured: one proposal, a crash, then a restart writing two more gave three lines on disk,
`p.jsonl:2 is not a proposal`, and both later proposals unreachable behind the glue. A crash that
cost nothing on its own became total loss the moment the process came back.

The lesson is not that Phase 14 was careless. The reasoning was sound about the scope it considered,
and the scope was one process. **An equivalence argument carries its assumptions with it**, and the
assumption worth writing down next to one is *what would have to change for this to stop being
true*.

This group's own equivalent mutant is named in `sinks.py` for that reason, with the arithmetic that
makes it equivalent rather than the conclusion alone.

---

### [NOTE] 2026-09-10 — Group 3: the net found nothing, which is what a net is for
Topics: contracts, invariants, td-004
Affects-phases: none
Affects-specs: none

Half the adapters had never been run against the contract suites, and wiring the missing ones found
**no defects at all**. Every one already answered the shared shape.

That is worth recording as a result rather than a shrug. It is the same wiring that caught nine mypy
errors the moment BUG-007's gate was widened, and here the same move caught nothing — which says the
adapters were built to the shape rather than merely tested into it. The value of the exercise is
what remains: the net, and the invariant that keeps it cast.

**What was not done is copy the seven names into a list.** A list of adapters is a list somebody has
to remember to extend, which is the failure that produced this row. The file scans for port
implementations and requires an answer for each, and it checks that a named module **really contains
a contract** rather than merely mentioning one — because a filename in a table is a promise and
nothing was making it one.

The scan also found more than expected: **29 implementations, not fourteen**. The runtime's own
testing doubles implement ports, are imported by hosts, and are therefore depended upon — so they
are contracted like anything else. Two adapters implement no port at all and never reach the file,
which is the honest answer for both: `mqtt` is a transport the devices adapter speaks over, and
`recording` exposes the registry outward, an arrow pointing the other way.

Since the net caught nothing, it was widened by one question while being cast: a known id called
with **inputs of the wrong shape**. That is D7 from its commoner side — a model misreading a schema
is far likelier than one inventing an id — and all eleven component ports already answered it too.

---

### [NOTE] 2026-09-10 — Group 3: three ways a test of a bound can fail to test anything
Topics: mutation, testing, td-005
Affects-phases: none
Affects-specs: none

Eleven mutations, three survivors, and all three were the tests rather than the code.

**Two rules could not be seen to work.** The invariant's predicates were inlined in their guards, so
deleting either body left the suite green — the real tree satisfies them, which is the whole point
and also the trap. `test_stands_alone.py` learned this twice under a mutation pass and its remedy is
now copied deliberately: each rule is written **once** as a function and called from both the guard
and a synthetic case built to break it.

**One arrangement took two attempts to become a test at all.** The claim was that the
least-recently-used shape is what gets evicted. The first version inserted `PLAN_CACHE_MAX - 1`
shapes, so the bound was never crossed and nothing was evicted under either policy. The second
crossed it and asserted the **end state** — which is identical either way, because a shape evicted
on one turn is re-planned and re-inserted on the next, so it is present by the time anyone looks.

What differs is not whether the shape is there at the end. It is **how often it had to be rebuilt on
the way**, and counting the misses is the assertion that could always have failed.

---
