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
