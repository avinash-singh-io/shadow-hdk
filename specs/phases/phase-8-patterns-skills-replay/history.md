---
type: History
phase: 8-patterns-skills-replay
---

# Phase 8 — history

Append only. Newest at the bottom.

### [DECISION] 2026-09-10 — D17: patterns and skills are TOML, and the check happens before the first turn
Topics: patterns, skills, toml, d17, loader, modes
Affects-phases: phase-9
Affects-specs: specs/architecture/adapters.md, specs/architecture/decisions.md

**TOML**, for two reasons rather than taste. A role file is multi-line prose, which JSON cannot hold
without escaping it into unreadability; and `tomllib` has been in the standard library since 3.11,
so the format costs no dependency. YAML would cost one and buy ambiguity — a version string that
parses as a float is not a hypothetical.

The second half matters more. `10` §306 says a skill declares its components *so skill and mode can
be checked against each other*. The check is the point, so it happens **before the first turn**,
against `RunContext.visible()`. A skill needing a component the deployment's mode forbids is refused
with the names of what is missing, rather than discovered three steps in when a tool call fails.

That is the same move as `visible()`: what the policy would refuse is **absent**, not greyed out
(`09` §4). A skill is simply the first thing that can say what it wants in advance.

*Rejected:* checking lazily, when the skill first calls a tool. It costs a model turn to learn what
a file could have said, and the failure arrives mid-work rather than as a refusal to start.

*Rejected:* a Python entry point per pattern. It makes the framework's patterns a different kind of
thing from a team's, which is exactly what `09` §5 says they must not be.

*Overturned by:* a pattern needing to compute something — a role varying with the deployment. That
would mean patterns want a template language, and the honest answer is then a template in the file
rather than a callable behind it.

---

### [ARCH_CHANGE] 2026-09-10 — Groups 0–2: patterns are files, skills are checked, big catalogues thin
Topics: patterns, skills, describe, d13, d17, toml
Affects-phases: phase-9
Affects-specs: specs/architecture/adapters.md

Five patterns ship as TOML under `library/`, read through `importlib.resources` so a wheel and a
checkout behave the same. Measured rather than assumed: `uv build --package
shadow-hdk-adapters-agent --wheel` puts all five files in the wheel.

A skill declares its components and is checked against `visible()` before the first turn. D13's
fourth and last mechanism, catalogue compaction, is built: above a pattern's threshold the model
sees names and one-liners and pulls a schema with `describe`.

### [DISCOVERY] 2026-09-10 — a mutation changed the skill design
Topics: skills, registration-ids, mutation-check
Affects-phases: none
Affects-specs: none

`missing_for` matched a component by **both** its interface name and its registration id. The
mutation removing the interface-name half survived every test, because in the tests those are the
same string.

Asking why the union existed answered it. `Invoke.component` takes the **registration id**, so an
adapter registering `search` under the id `brave:search` makes only one of the two addressable.
Matching both would let a skill declare a need it could not then invoke — a check that says yes to
something the runtime will not resolve. It now matches ids only, and a test covers a registration
whose id and interface name differ.

Worth the entry because the mutation did not find a missing test; it found a design that was wrong
in a way no test could have been written for while the union stood.

### [DISCOVERY] 2026-09-10 — the benchmark flaked a second time, and the cause had moved
Topics: benchmark, d11, flake, subprocesses
Affects-phases: none
Affects-specs: none

`test_a_hundred_sequential_steps` failed at **309.9 ms** against its 300 ms ceiling, and measured
**56.9 ms** alone a minute later. Its own docstring predicted this, from a first occurrence at 308 ms
during a run spawning MCP subprocesses.

The cause has changed, though. Contention is now **inside the suite** rather than beside it: tests
that spawn subprocesses for the sandbox, the recording server and held children all run before this
one, and three samples can all land while the machine is still settling.

Best of **nine** rather than three: it costs about half a second and gives the minimum a real chance
at a quiet moment. Raising the slack was rejected — it buys quiet by making the gate unable to fail,
which is the failure the docstring already warns about. Two consecutive full-suite runs green
afterwards, and the number is unchanged at 0.577 ms a step.

---

### [DECISION] 2026-09-10 — D18: compaction is a meta-tool, which is what "not a runtime power" means
Topics: compaction, d3, d18, patterns, sink
Affects-phases: none
Affects-specs: specs/architecture/adapters.md

`09` §5 calls compaction *a component, not a runtime power*. The contrast is the load-bearing half,
and a **meta-tool** honours it more exactly than a component would.

A component would be registered for every run whether or not a deployment wants its agent rewriting
its own history; a meta-tool is the pattern's, so a team that does not want it simply does not list
the verb. And a component cannot reach the transcript — it could propose a summary and never
actually shorten anything, which is a compaction in name only.

So the summary reaches the **sink** as a `Proposal(kind="compaction")` and the adapter writes it
nowhere, and the loop's own transcript is shortened. What may be dropped is the middle: the role the
agent was given and the request it was asked to answer are not the model's to summarise away.

### [ARCH_CHANGE] 2026-09-10 — Groups 3–4: replay, compaction, and the model's helper verbs
Topics: replay, compaction, spawn, send, release, d16, d18
Affects-phases: phase-9
Affects-specs: specs/architecture/runtime.md, specs/architecture/adapters.md

`RecordedModel` records a run's model calls and replays them for nothing. Two modes, not a fallback:
recording always calls through; a replay-only port has no inner model, so a stale tape fails loudly
instead of quietly costing money. There is deliberately no third mode that replays what it knows and
records what it does not.

Phase 7's deferral lands: `spawn` / `send` / `release` as meta-tools, with the child's shape decided
here because that is what made them a Pattern concern — a helper is *the named agent given a brief,
then a wait on the mailbox*, which is D16's held child written as a composition. A sixth pattern,
`keeps-helpers`, ships with the verbs.

### [DISCOVERY] 2026-09-10 — a bug only the end-to-end test could find
Topics: replay, fingerprint, tests
Affects-phases: none
Affects-specs: none

`fingerprint` sorted the offered tools as parsed dicts, which raises the moment a request carries
more than one — and every unit test offered exactly one, so `sorted` never compared anything and all
eight passed. It surfaced when a real agent run went through with a catalogue: the whole step came
back `Failed` with a TypeError about dicts.

Sorted as text now, and the unit tests offer two tools by default. The lesson is narrower than
"write end-to-end tests": a test that exercises a collection with **one** element does not exercise
the collection.

### [DISCOVERY] 2026-09-10 — Phase 7 woke a held child on a ceiling its parent could no longer afford
Topics: leases, held, children, phase-7
Affects-phases: none
Affects-specs: none

`send` and `release` re-carved the ceiling the child was *spawned* with. A parent that had spent in
between could no longer afford it, so the carve refused — and a coordinating agent that spawned a
helper and took two more turns could neither message nor release it. Phase 7's own tests missed it
because their parent spends nothing between spawning and sending.

A held child is now woken within what the parent has left. The regression test lives in
`tests/runtime/test_children.py`, where the bug does, rather than where it was noticed.

### [DISCOVERY] 2026-09-10 — three survivors in tests that looked complete
Topics: mutation-check, tests
Affects-phases: none
Affects-specs: none

The helper verbs' first mutation run left three survivors, and none was a missing test — all three
were assertions too loose to tell right from wrong:

* the invented-handle test asserted only that `@9` appeared, which cannot distinguish *there is no
  helper @9; spawn one first* from *that did not work: KeyError: @9*;
* nothing covered a deployment with **no mailbox**, where a helper cannot park and must be reported
  as finished rather than held — otherwise the model is handed a handle for something already gone;
* the release test asserted the word "released" without checking anything stopped, so a verb that
  leaked helpers would have passed.

---
