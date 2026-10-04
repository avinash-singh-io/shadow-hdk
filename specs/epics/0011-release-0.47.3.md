---
type: Reply
---

# Lane H — 0.47.3 candidate, H8 / BUG-240

**Published and verified:** [v0.47.3](https://github.com/avinash-singh-io/shadow-hdk/releases/tag/v0.47.3),
2026-10-04. The prepared branch is merged. All seven PyPI files, fresh installation and Linux
helper resolution are verified; see `../phases/phase-66-the-short-list/evidence/published-0.47.3.json`.

**Historical preparation snapshot follows. Its pending status and commands precede publication.**

Not published. Existing cache read/write counters now survive the key-backed loop's aggregation,
output and model-session reconstruction, reaching persisted records and existing wire events.
See [`0.47.3.md`](../../docs/migrations/0.47.3.md). Known zero and unknown stay distinct.

## Release order

Publish frozen 0.45.0, 0.46.0, 0.47.0, 0.47.1 and 0.47.2 first, one at a time, then
`codex/release-0.47.3`. Do not land the moving phase branch. This completes authorized train
implementation; owner publication and phase landing remain.

## Owner commands

From a clean repository after the prior release is published. Equality checks stop this block
if upstream changed; re-gate the resulting tree rather than bypassing them.

```bash
(
set -e
git fetch origin
git switch staging
git merge --ff-only origin/staging
git merge --no-ff origin/codex/release-0.47.3 -m 'merge: H8 checkpoint into staging'
git diff --exit-code origin/codex/release-0.47.3 staging --
touch .momentum/merge-approved && git push origin staging
git switch main
git merge --ff-only origin/main
git merge --no-ff staging -m 'merge: staging into main for v0.47.3'
git diff --exit-code origin/codex/release-0.47.3 main --
touch .momentum/merge-approved && git push origin main
git tag -a v0.47.3 -m 'release: v0.47.3'
git push origin v0.47.3
gh release create v0.47.3 --title 'v0.47.3' --notes-file docs/migrations/0.47.3.md
)
```

Wait for build/helper/publish/smoke, then verify both distributions and all seven files, plus a
fresh install outside CI. A Linux install must resolve the matching helper. Update published
status only after that evidence, then close the phase through its normal owner landing/release process.

## Verification Evidence

Nine of ten new cases failed before implementation; the all-unknown wire case already passed.
All ten now pass on source and on a fresh installed wheel outside checkout. Twenty targeted
mutations bite, covering aggregation, both output axes, reconstruction, unknown/zero distinctions,
thread metering and wire serialization. All 55 earlier train mutation checks were re-run and bite
with source bytecode cleared before each mutant and bytecode writes disabled (TD-021).
Full gate: **2,274 passed, 8 skipped, 24 deselected**, exit 0 with disposable PostgreSQL enabled; lint/format/types clean. Wheel/sdist build; all 165 Python package sources match the wheel; schemas and
TypeScript regenerate without drift. Owner publication remains pending.
