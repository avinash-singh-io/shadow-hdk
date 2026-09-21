---
type: Retrospective
status: complete
epic: the-harness-as-data
---

# Phase 36 — plan admission — Retrospective

**Released as v0.31.0** · eight groups, 2026-09-18 · `phase-36-plan-admission`

## What this phase set out to do, and what it came to

A plan an agent, a CLI or a host proposes is now judged **whole, before anything compiles** — its
shape against limits that narrow host → mode → parent, every named component's existence, and a
dry judgement of every leaf's declared effects — with every mismatch named as data. Planning
reaches the runtime through a registered component, so a resident CLI plans exactly as the kit's
own loop does. A plan may run after its planner. A parked plan can be amended on the record. And
a behaviour field the provider cannot take is named rather than dropped.

Ten acceptance criteria; eight met as written, two named in `overview.md` as coming out
differently — criterion 3 amended (below) and criterion 5 proven on one CLI rather than two.

## What went well

**The grammar did not move.** D107 said a plan is a `Composition` and a harness is data. Nothing
in this phase needed a new step kind, a second workflow language, or a parallel path for "plans"
beside "calls". `admit()` sits in the kernel beside `check_compatibility` and measures; the
runtime judges. A single call is still literally a plan of one step, which is why every caller —
the model loop, the `compose` component, the offer, the wire — got admission by entering
`children.spawn` and nothing else.

**One path, proven by what it broke.** Putting admission inside `spawn` rather than at three call
sites meant three callers had to be adapted honestly, and each one taught something: the loop's
`compose` answers the model with every mismatch; the `spawn` helper verb had been leaning on a
mailbox step *failing* and now composes only what is offered; the offer returns a refused
one-call plan as the error a CLI already read. A fourth — BUG-001's guard — refused the registered
`compose` as a tool shadowed by the meta-tool, which turned out to be the right question asked at
the wrong layer: for the loop, a plan-labelled registration *is* the meta-tool.

**RED first held all the way down.** Every group opened with a failing test for the stated reason,
and the mutation checks bit each time: admission removed from `spawn` (6 scenarios), the depth
check removed (2 corpus cases), `meet` widened (2 properties), the widening refusal removed (1),
the turn ignoring the mode's limits (2), no amendment admission (4), the deferred plan never run
(1), the replay draining removed (2). The corpus was frozen before the loop it measures, and never
edited again — Rule 11 as intended.

**The live proof landed, and closed something older.** Codex CLI 0.154.0 proposed
`fan_out(read_a, read_b)` through the socket; both steps ran through our registry; the reply named
both contents. That is also the first end-to-end proof of the registry relay on Codex, which
`codex.toml` had called unproven since the quota ran out one turn short — the comment is now the
measurement.

## What did not go well

**Two decisions were wrong until the code said so.** D108 and D121 had admission *raise* the
plan's question and *refuse* a plan containing a step the policy would refuse. Implementing that
against the whole suite showed the collision: raising the question at admission failed where no
`Questions` handle exists (breaking D57's park) and asked twice where one does; refusing the plan
for a refusable step broke BUG-012's promise that the plan runs and the planner sees every result.
Admission now refuses only what no step can see — structure and existence — and *names* the asks
and refusals it found. The lesson is not that the decisions were careless: it is that a decision
about **where** a judgement belongs cannot be settled from outside the code that already makes
that judgement somewhere else. Epic 0009's amendment section carries it, pending the owner.

**BUG-055 was found by a test written for something else.** The wire test for `thread/amend` —
refused, then admitted, on one thread — failed with the first amendment's mismatch on the second
call. LangGraph replays a task's earlier resume values by index on every re-run, so a component
that parks twice in one step gets answer one at the first `interrupt()` and the new answer at the
second, which was the *parking* call. G5's tests parked once each and never saw it. A P1 in the
resume path, in the tree since D57, found only because the wire scenario did the same thing twice.
Scenarios that repeat an operation are worth more than their line count suggests.

**The Claude Code half of the live measurement is still owed.** The machine is signed out
(`loggedIn: false`), so criterion 5's "identical events on a resident CLI" is proven for Codex and
not yet for a second CLI. It is one turn's work once signed in, and it is the owner's to unblock —
not something to paper over by calling the criterion met.

**The stale `.pyc` trap bit again.** A same-size edit inside the same second left a stale cache and
a mutation check that lied. `rm -rf __pycache__` is the fix, and this is the second phase to spend
time on it.

## Lessons

1. **Admission is a different question from authorization, and the code has to keep them apart.**
   The plan is judged whole; the act is authorized at the act (Phase 33). Naming a plan's asks up
   front lets a host present one card without letting consent stand in for authority.
2. **Put a new gate where every caller already passes,** not where it is convenient to write. The
   gate in `spawn` made admission true for the wire without a wire-specific line.
3. **A decision that says *where* something happens is a hypothesis about code you have not read
   yet.** Record it, implement it, and amend it in the open when the tree disagrees.
4. **An operation worth doing twice is worth testing twice in a row.** BUG-055 existed for four
   phases behind tests that each did it once.

## Carried out of the phase

- **ENH-021** — the React demo re-pinned to 0.31.0 with a chapter from the live run. It consumes
  the kit from PyPI, so it cannot be true before the publish; the same order 0.29.1's chapter
  followed.
- **Owed to the owner** — the Epic 0009 amendment (D108/D121), the Claude Code half of the live
  measurement, and the ecosystem board's H36 row, Pins and Log line (that repository is on another
  session's branch).
- **BUG-050** rewrote the decisions index again on `momentum okf index`; restored from a copy, for
  the fourth phase running. It belongs in momentum or a project index hook.

## Verification Evidence

Captured fresh at completion, 2026-09-18, on `phase-36-plan-admission` at the tree that was
tagged. Every command exit 0.

### Build — `build_command` from `specs/config.md`

```
$ uv sync --all-packages --all-extras
Resolved 137 packages in 3ms
Checked 130 packages in 12ms
exit=0
```

### Tests — `test_command`, the whole non-live suite

```
$ uv run pytest -q -m 'not live'
… (70 earlier lines)
    PydanticSerializationUnexpectedValue(Expected `Spawned` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanAdmitted` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanRefused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Held` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `UsageReported` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Reasoning` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ModeChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `WorkspaceChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Ended` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    return self.serializer.to_json(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1773 passed, 14 skipped, 13 deselected, 85 warnings in 163.43s (0:02:43)
exit=0
```

### Lint

```
$ uv run ruff check .
All checks passed!
exit=0
```

### Format

```
$ uv run ruff format --check .
505 files already formatted
exit=0
```

### Types

```
$ uv run mypy .
Success: no issues found in 452 source files
exit=0
```

### The published bundle

```
$ momentum okf check .
✓ specs/ is an OKF v0.1 conformant bundle (194 markdown file(s))
exit=0
```

### The generated TypeScript client

```
$ npm run generate && npm run check && npm run build

wrote 28 contracts under /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/clients/typescript/src/schemas and /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/clients/typescript/src/schemas.ts
> tsc --noEmit -p tsconfig.json

> tsc -p tsconfig.json

exit=0
```

### Fresh-install smoke — the 0.31.0 wheel built, installed into a clean venv, imported, and answering `initialize`

```
$ uv build && uv venv fresh && uv pip install …/shadow_hdk-0.31.0-py3-none-any.whl && shadow-hdk serve --stdio
Successfully built /private/tmp/claude-501/-Users-avinash-Workspace-Projects-shadow-hdk/292e7e94-f4c9-4640-a939-f084271247fd/scratchpad/smoke2/dist/shadow_hdk-0.31.0.tar.gz
Successfully built /private/tmp/claude-501/-Users-avinash-Workspace-Projects-shadow-hdk/292e7e94-f4c9-4640-a939-f084271247fd/scratchpad/smoke2/dist/shadow_hdk-0.31.0-py3-none-any.whl
imported 0.31.0
"protocol_version": "3"
exit=0
```

### Live — the resident CLI planning through the socket (Group 3)

```
$ uv run pytest -m live tests/test_a_cli_plans_through_the_socket.py -rs
1 passed
```

Codex CLI 0.154.0, 2026-09-18: the CLI proposed `fan_out(read_a, read_b)` through the socket; two
`plan_admitted` on the record (the one-call plan for the `compose` call, then the proposed plan);
both `read_file` steps ran through our registry; the reply named both contents. 2 turns, 4 steps,
17.4 s, 57,471 in / 324 out tokens, unpriced. Claude Code is signed out on this machine, so the
second CLI's half of criterion 5 is owed.
