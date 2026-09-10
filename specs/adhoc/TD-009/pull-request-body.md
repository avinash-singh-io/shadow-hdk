# Phases 0–18: the harness, and the audit's P0s and P1s

One pull request for a linear stack of 141 commits. Each phase branched from the one before, so
every phase branch is an ancestor of this one and there is nothing to land separately.

**This is the first time CI will have run on any of it.** The workflow triggered only on pushes to
`main` and `staging` and on pull requests, and nothing has ever reached either — so every "four
zeros" in every commit message below is one laptop's word. Widening that trigger is the last commit
in the stack (TD-009). Read a red here as information, not as a regression.

## What is here

A generic agentic system: a runtime that runs an agent over an open set of components under a
governance policy, and hands what it produces to whoever is listening. It governs **effects, not
names** — a six-field `EffectProfile` with a `narrows` partial order — and the agent's plan is data
compiled to a LangGraph graph.

Seventeen distributions, all `0.12.0`, all MIT: kernel, runtime, wire, and 14 adapters.

| | |
|---|---|
| Tests | 837 passed, 1 skipped, 10 deselected |
| Types | mypy strict, 132 files |
| Lint | ruff check and format, clean |
| Coverage | `shadow_hdk.runtime` above the 90% floor, measured locally |

## The audit

A full-codebase audit on 2026-09-10 filed eleven bugs and seven tech-debt items. **Every P0 and
every P1 is closed here**, and two of them corrected claims this lane had previously made:

* **BUG-007** — `mypy_path` omitted three packages, so every mypy-0 reported from Phase 9 to Phase
  16 had silently excluded the wire, where nine errors sat. The gate covers all 132 files now and
  an invariant asserts it.
* **BUG-010** — the audit's own row was wrong about one case, and the backlog row says so rather
  than being quietly closed.

The four P0s: the lease reset at every pause (D33); an assistant message never carried the calls it
made; `resume` over the wire always raised while `serve` had no trust boundary (D34); and the gate
itself.

The six P1s: a hard link escaped the workspace; a step did not own the process tree it started
(D35); a containment proof was a banner match a five-line fake could satisfy (D36); a parked parent
lost its children (D37); a parked step re-ran from the top, letting a re-run judgement overturn a
human's answer (D38); the ACP purse charged every turn again and could not stop a deaf child; five
promises the agent adapter made and kept nowhere.

## Reviewing it

The commits are the argument. Each says what was measured, what was rejected and why, and —
where it applies — which of its own tests turned out to encode the bug they were meant to catch.
`specs/status.md` is the state of the world; `specs/architecture/` is the design;
`specs/architecture/diagrams/` holds five views of it.

Nothing is tagged. The tag is the owner's.
