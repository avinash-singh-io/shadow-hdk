---
type: Retrospective
status: complete
epic: production-boundary
---

# Phase 33 retrospective — Authority at the act

## Outcome

Phase 33 turns controlled irreversible work into a durable host-governed transaction. The runtime
stages the exact call, obtains a bound single-use authorization, rereads authority at the component
boundary and records the transition through receipt, failure, refusal or explicit unknown. The
journal is authoritative; events, items, schema and telemetry are projections. The result promises
at-most-one runtime invocation for a recorded stage, not fictional exactly-once delivery across an
external system.

The ready-made `ServeHost`/`Harness` owns reference authority, authorization and a durable journal;
custom hosts can replace those ports. Remote irreversible calls without that boundary are observed,
not described as controlled. Protocol 3 publishes the generic `effect_recorded` lifecycle and
refuses older peers.

## What went well

- The frozen transaction corpus made legal state order, stale authority, grants, crashes and
  reconciliation concrete before implementation.
- The complete non-live gate exposed real compatibility seams in direct `Ports` fixtures and a stale
  release-smoke protocol, both repaired before release.
- A clean installed-wheel smoke confirmed the package reports and accepts protocol 3.

## Lessons

- Approval is durable evidence of consent but cannot substitute for current authority at the act.
- “Controlled” is a stronger claim than “observed”; it requires the complete host transaction
  boundary, not merely an event after an external call.
- Package and wire versions are intentionally separate; release smoke must derive the latter from
  the installed artifact.

## Verification Evidence

### `uv sync --all-packages --all-extras && uv build && uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest -q -m 'not live'`

Exit code: 0

```text
Successfully built dist/shadow_hdk-0.30.0.tar.gz
Successfully built dist/shadow_hdk-0.30.0-py3-none-any.whl
All checks passed!
493 files already formatted
Success: no issues found in 441 source files
1688 passed, 14 skipped, 12 deselected, 85 warnings in 158.83s
```

### `npm run generate && npm run check && npm run build; uv run twine check dist/*; momentum okf check .`

Exit code: 0

```text
wrote 24 contracts under clients/typescript/src/schemas
tsc --noEmit: passed
tsc build: passed
Checking dist/shadow_hdk-0.30.0-py3-none-any.whl: PASSED
Checking dist/shadow_hdk-0.30.0.tar.gz: PASSED
specs/ is an OKF v0.1 conformant bundle (186 markdown file(s))
```

### Fresh installed-wheel protocol smoke

Exit code: 0

```text
shadow-hdk==0.30.0 installed from dist/shadow_hdk-0.30.0-py3-none-any.whl
{"jsonrpc": "2.0", "id": 1, "result": {"protocol_version": "3", "version": "0.30.0"}}
```
