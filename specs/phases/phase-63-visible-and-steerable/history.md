---
type: History
---

# Phase 63 — history

> Append-only. One entry per meaningful change, logged when the decision was fresh (Rule 8).

### [DECISION] 2026-10-01 — the plan is a component with no effects at all
Topics: plan, components, effects, modes
Affects-phases: none
Affects-specs: docs/migrations/0.42.md
Detail: D171, and the row asked for this decision explicitly ("decide first whether this is a
battery the kit ships or a shape it documents"). A component, for two reasons, and the second
decides it: the boundary rule puts a plan's content in the product, and an empty `EffectProfile`
means every mode admits it — `read-only` included. An agent that had to ask permission to say what
it intends would stop saying it, and a narration nobody can afford is worse than no narration. The
revisions reach the record for nothing extra, because `Invoked.inputs` already carries them in
order, which is the real argument for a component over a runtime concept.

---

### [DECISION] 2026-10-01 — a plan item's status is an open string
Topics: plan, vocabulary
Affects-phases: none
Affects-specs: docs/migrations/0.42.md
Detail: D172. The same cut `Provider.transport` and `injects_tools` make: a `Literal` would mean the
kernel's contract changes every time a product wants a status it did not think of, and a plan's
vocabulary is exactly what a product owns. A mutation turning it into an enumeration fails a test,
so this is pinned rather than merely intended.

---

### [DECISION] 2026-10-01 — a steer is delivered between steps, and the bool stays honest
Topics: steer, key-backed, loop
Affects-phases: none
Affects-specs: docs/migrations/0.42.md
Detail: D173. `ModelAgent.steer` answered `False` and the row said why: the loop between steps is
the kit's own, so it is the one place it could be true. Queued and folded in as the person's words
before the next model call — **not** into a request already in flight, because that request cannot
be changed and pretending otherwise would make the `bool` a lie. A turn that has ended still answers
`False`, and a one-shot dialect always will.

---

### [NOTE] 2026-10-01 — the test asserts the words reached the model, not that steer said yes
Topics: steer, verification
Affects-phases: none
Affects-specs: none
Detail: Returning `True` is the easy half and the half that could be wrong on its own. The test
holds the model inside its first call, steers, releases it, and then asserts the words are in the
**second** request and absent from the first. The second assertion is defensive rather than
mutation-sensitive — a request already sent cannot be retroactively changed, so no realistic
mutation makes it fail — and that is worth saying rather than counting it as evidence.

---

### [DISCOVERY] 2026-10-01 — the session-level `steer` refusal was untested
Topics: steer, verification, tdd
Affects-phases: none
Affects-specs: none
Detail: Fourth mutation-found weakness this epic. `test_a_steer_with_no_turn_running_is_false` asked
the *thread*, and `Conversation.steer` short-circuits on "is a turn running" before it ever reaches
the provider — so making `_ModelSession.steer` return `True` broke nothing. The test now asks the
session directly, and a second test covers the thread's own reason for refusing. The recurring
lesson across this epic: a test that cannot say *which* layer refused is not testing the layer its
name claims.

---

### [NOTE] 2026-10-01 — gate green, and the epic's arithmetic
Topics: verification, release
Affects-phases: none
Affects-specs: specs/status.md
Detail: `ruff check` clean, `ruff format --check` 558 files, `mypy` strict 496 source files,
`pytest` **2021 passed, 20 skipped, 23 deselected**, exit code read directly. The epic entered at
1897 and leaves at 2021: **+124 tests** across Q1 and phases 59–63, with 63 mutations verified to
bite and six of them having found assertions weaker than they looked.

---
