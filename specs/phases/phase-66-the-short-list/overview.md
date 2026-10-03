---
type: Phase
status: in-progress
tags: [h10, h11, h20, h23, h6, h7, h8, lane-p, maintenance, open-standards]
deps: [phase-65-the-claims-are-true]
---

# Phase 66 — the short list

> **Phase numbering collides with `shadow`.** This repository's 59–66 and `shadow`'s 59–66 are
> different work that shares numbers. Nothing here names a `shadow` phase by number without saying so.

## Goal

The owner's decision of 2026-10-03, after lane P's cross-repo plan: **HDK takes a short list and then
goes to maintenance only.** Six items, in order. Everything else in lane P's forty-three — H12–H17,
H21, H22, H29, H30, H41–H43 — **belongs to Shadow and is not to be built here.**

This is the last phase of the bridge. After its release the kit takes bugs and the product's pins.

## Scope, in the owner's order

| | item | what it is |
|---|---|---|
| G1 | **H10** | what moves to Shadow, stated per contract — D153's standing requirement, unmet by seven phases |
| G2 | **H11 confirm** | which parts of *an agent definition honoured on every provider* are actually missing — **reported before anything is built** |
| G3 | **H20** | full diffs: a host-set cap and a governed door to fetch a recorded change's whole diff later |
| G4 | **H23** | a governed Codex run carries only the tools it was given |
| G5 | **H11 remainder** | whatever G2 found, built |
| G6 | **H6–H8 confirm, then fix** | three more claims the kit makes and may not keep |
| G7 | the release: migration note, version, changelog, status, the reply to lane P |

## Standing constraints (the owner, 2026-10-03)

- **Use open-source software where it does the job, and follow open standards.** This kit already
  does in the places that matter — MCP for tools, ACP for editors, `SKILL.md` and `AGENTS.md` for
  instructions, OpenTelemetry's GenAI conventions for traces, unified diff for changes. Each item
  below says which standard it is held to, and **nothing here invents a format where one exists.**
- **Nothing from the Shadow list.** Named above so a later reader does not mistake absence for
  oversight.

## Decisions

G1's is D184, in [`planning/what-moves-to-shadow.md`](/planning/what-moves-to-shadow.md).

| # | Decision | Rationale |
|---|---|---|
| D185 | **The cap on a change's diff is the host's** — an int, or `None` for the whole of it — defaulting to what it has always been | a product showing a diff panel knows what it can render and the kit does not. The old comment said *a host that needs the whole change reads the file*, which was never true for a contained or remote environment, and that is the case this record exists for. All four call sites had taken the one constant, so lane P's workbench showed 4 KB per file because nobody could choose otherwise |
| D186 | **A cut diff is kept whole, by handle, in a bounded hold, and fetched through a governed read** paging by `handle`/`start`/`length` | raising the cap for every change to suit the largest one makes every record bigger, so the honest shape is a small diff on the record and a door to the rest. `recall`'s idiom deliberately (D47): one shape for *a result too large to show whole*, not two. Bounded because holding every cut diff for an environment's life would keep the content of every file an agent ever touched — a leak and a privacy problem nobody asked for — so a handle exists only for a cut diff, the oldest go first, and an evicted one is refused with *it was dropped*, which is a different fact from *no such handle* |
| D187 | **Codex's strict mode is `--ignore-user-config`**, applied only when tools are injected | ENH-005 concluded Codex needed the equivalent of `--strict-mcp-config` upstream and shipped that in the record's prose; the flag existed on the same version all along. Our own servers travel as `-c` command-line overrides so they survive it, and auth still uses `CODEX_HOME` so a subscription login survives it. Applied only for a governed launch, because a launch injecting nothing has no business dropping a person's configuration |

## Verification

TDD strict, every assertion mutation-checked, mindful of TD-019 (a failing test that stands up a
`ServeHost` hangs, so logic is extracted into pure functions and checked there).

Two standing rules this phase inherits from 65, both earned:

- **A mechanism with two doors needs a test at each.** BUG-235 passed every test in its group because
  they all went in through the door that refuses, never the door that offers.
- **If a property is arithmetic, prove it with arithmetic.** A wall-clock margin is something a
  loaded machine can eat; one of 65's own tests became a TD-018 flake that way.

And one specific to G2 and G6: **confirm against the source and report before building.** Three of
phase 65's five items needed a different fix than the audit assumed, and two were already partly
built. An hour of reading changed the shape of the work twice.
