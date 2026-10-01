---
type: History
---

# Phase 64 — history

> Append-only. One entry per meaningful change, logged when the decision was fresh (Rule 8).

### [DECISION] 2026-10-01 — an agent is a store row like a skill is
Topics: agents, patterns, store, plugin-boundary
Affects-phases: none
Affects-specs: docs/migrations/0.43.md, docs/for-a-product.md
Detail: D174. `pattern_from(data, where=)` already existed, so the data constructor was done and
only the source was missing. `StorePatterns` mirrors `StoreSkills` exactly — version-gated reload,
a malformed row skipped rather than fatal, `skipped` saying why. A seventh concept with a seventh
mechanism would have been the asymmetry this phase exists to remove.

---

### [DECISION] 2026-10-01 — a mode names its agent
Topics: agents, modes, governance
Affects-phases: none
Affects-specs: docs/migrations/0.43.md
Detail: D175. A mode already carries who the model should be (`behaviour`, D64) and what it may do
(policy, plan limits); which loop runs it is the same kind of fact. Putting it there means a product
switches agent through `set_mode` — a door that exists and is governed — rather than an ungoverned
new one. The cost, named at the time and accepted: a Reviewer that should run in two environment
modes needs two mode rows. `thread/start {agent}` is the per-thread override that softens it.

---

### [DECISION] 2026-10-01 — an unknown agent is refused, never a silent default
Topics: agents, refusal
Affects-phases: none
Affects-specs: docs/migrations/0.43.md
Detail: D176. Falling back to `single` would hand a product a run that looks right and is not. The
same cut `Dialect` makes for an unknown transport and `ModeRegistry` for an unknown mode id. The
refusal names what *does* exist, because a name that is not there is usually a typo and the fix is
the list; and it happens before an environment is opened or a model asked, so it costs nothing.

---

### [DISCOVERY] 2026-10-01 — full plugin CRUD already existed and was documented nowhere
Topics: store, wire, documentation, product-boundary
Affects-phases: none
Affects-specs: docs/for-a-product.md
Detail: Found while auditing what a product can own. `store/put`, `store/get`, `store/delete`,
`store/list` and `store/version` are on the wire **with no collection allow-list**, so creating,
updating, listing and deleting skills, modes, rules, batteries and providers has worked for a long
time. Lane P asked us for that capability without knowing they had it. That is a documentation
failure of ours, and it is why ENH-026 was pulled into this phase rather than deferred a ninth
release — the refresh's opening chapter is now that surface.

---

### [DISCOVERY] 2026-10-02 — the repo's own invariant is this phase's thesis
Topics: registries, store, invariants
Affects-phases: none
Affects-specs: none
Detail: `tests/invariants/test_every_registry_has_a_store_source.py` asserts that every registry
takes a `Store`, because *a registry filled only from code or files is a restart waiting to happen*
(principle 10, D66). It went red the moment `PatternRegistry` existed — the agent gap had escaped it
only because there was no registry to catch. Registered with `store_patterns` and its proof. Worth
recording because the invariant stated the phase's argument before the phase did.

---

### [DISCOVERY] 2026-10-02 — TD-019: a failing `ServeHost` test hangs, so those paths cannot be mutation-checked
Topics: verification, tests, mutation
Affects-phases: none
Affects-specs: none
Detail: Reproduced five times across G2 and G3. A test that stands up a `ServeHost` — and so a real
`LocalEnvironment`, whose sandbox proof spawns subprocesses — passes in about a second, but the same
test with one line mutated never returns: not under `--timeout=25 --timeout-method=signal`, not with
the thread closed in a `finally`. Non-`ServeHost` tests in the same files fail cleanly in under a
second. Since project-rules requires every assertion to be mutation-checked and a hang is not a
result, the logic under test was extracted into pure functions (`agent_recorded`) and checked there,
with the `ServeHost` tests kept as behavioural coverage. That is a better design independently, but
it is a workaround and TD-019 records the wall.

---

### [NOTE] 2026-10-02 — three mutation passes were wrong before one was right
Topics: verification, mutation
Affects-phases: none
Affects-specs: none
Detail: Worth recording because the second was the dangerous one. The first stalled on `uv run` lock
contention with a still-running suite. **The second was vacuous**: a shell helper that never passed
its arguments to python, so no mutation was applied and all seven cases reported success — a
mutation pass that silently applies nothing is worse than none, because it reports green. The third
applied correctly and hung. Only the fourth, at unit level, produced usable results. The helper is
now a script that fails loudly on a missing anchor.

---

### [NOTE] 2026-10-02 — two corrections made while building
Topics: wire, ports
Affects-phases: none
Affects-specs: none
Detail: The wire first passed `agent=` to `ThreadHost.open` unconditionally, which broke **22
tests** — every host double written before the field existed. That is exactly what D14 forbids
("growing this port broke no adapter"), so it is passed only when given. And `ServeHost.open`'s new
`agent: str` parameter shadowed the local holding the `AgentPort`; the local is now `provider_agent`.

---

### [NOTE] 2026-10-02 — gate green
Topics: verification, release
Affects-phases: none
Affects-specs: specs/status.md
Detail: `ruff check` clean, `ruff format --check` 530 files (down from 562: `docs` now excluded,
TD-017), `mypy` strict 499 source files, `pytest` **2058 passed** at G3; the close-out gate is
below. Phase 63 left the suite at 2021.

---
