---
type: Retrospective
status: complete
epic: production-boundary
---

# Phase 32 retrospective — One agent surface

## Outcome

Phase 32 removes the product-facing lifecycle split between model APIs and resident agent CLIs.
`ModelAgent` adapts a `ModelPort` below the existing `AgentPort` and `Thread`; the same capability
selection, tools, parking, holding, usage, activity, interruption and resume now apply to either.
Items carry bounded invocation inputs, reconnect behavior lives in a reusable runtime primitive,
silent links recover, and production bearer input stays out of process arguments.

This is the second Epic 0008 checkpoint. It is complete, pushed and unreleased. Intent Studio was
not modified, and no phase tag, protected-branch merge or package release was created.

## Test-first evidence

| Group | RED observed before implementation | GREEN evidence |
|---|---|---|
| 0 — lifecycle evaluator | imports/contracts failed only on absent model agent, inputs, stream and bearer boundaries | locked cross-provider scenario plus adversarial item/session/auth cases |
| 1 — model below AgentPort | blocked provider call survived Thread interruption | 187 focused lifecycle checks; three destructive mutations |
| 2 — invoked inputs | the fold/schema/client omitted inputs | 67 focused checks and three destructive mutations |
| 3 — shared stream session | no transport-independent state machine existed | 22 state/property/D94 checks and four destructive mutations |
| 4 — link and bearer hardening | HTTP had no heartbeat, client no silence deadline, production token only argv | 20 focused checks and five destructive mutations |

## Final verification evidence

- `uv sync --all-packages --all-extras` and `uv build` produced the 0.29.1 sdist/wheel candidate.
- `uv run ruff check .` passed; `uv run ruff format --check .` found 480 files formatted.
- `uv run mypy` passed over 429 source files.
- `uv run pytest` passed 1,625 tests; 12 expected skips and 12 live tests were deselected.
- Explicit lifecycle, item, stream, reconnect, bearer and benchmark selection passed 30 tests.
- Document, decision, TypeScript drift, wire parity and schema selection passed 61 tests.
- TypeScript check/build and deterministic silence smoke passed; the smoke reattached from cursor 1.
- `momentum okf check .` validated 185 Markdown specs.

## Findings

- BUG-050 records that the generic OKF indexer would erase the distributed canonical decision map;
  the output was rejected and the existing D1–D106 index preserved.
- BUG-051 records an unraisable ACP subprocess-transport cleanup warning.
- TD-012 records AMQTT configuration/plugin APIs marked for removal.
- BUG-049 was deprecated after direct re-reading and tests proved the suspected duplicate frame was
  the intended replay loop followed by the live loop.

## What carries forward

Phase 33 must keep capability and consent separate from act-time authority. Its evaluator starts
from the approved D99–D104 transaction: stage, authorize against the current revision, execute once,
then reconcile into an append-only journal with explicit unknown outcome and no blind retry.
