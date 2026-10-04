---
type: Reply
---

# Lane H — 0.46.0 candidate, H11-C

**Published and verified:** [v0.46.0](https://github.com/avinash-singh-io/shadow-hdk/releases/tag/v0.46.0),
2026-10-04. The prepared branch is merged. All seven PyPI files, fresh installation and Linux
helper resolution are verified; see `../phases/phase-66-the-short-list/evidence/published-0.46.0.json`.

**Historical preparation snapshot follows. Its pending status and commands precede publication.**

Not published. The new item is stored plan-limit parsing through the existing contract parser;
actual planned execution changes under a stored bound. All three axes parse, absent or null
limits defer to the run, malformed values refuse, and loop-tuning knobs remain excluded.
See [`0.46.md`](../../docs/migrations/0.46.md). The migration table now records C as built;
D remains unbuilt. No new decision was needed and no product pin was changed.

## Release order

Land and publish `codex/release-0.45.0` first, using the earlier lane P reply. Then land the
independently frozen `codex/release-0.46.0`; do not merge the moving phase branch for either
release. Each checkpoint gets its own GitHub Release and publication verification. The owner
authorized continued preparation while those publication steps remain pending.

## Owner commands

From a clean repository after the prior release is published. Equality checks stop this block
if upstream changed; re-gate the resulting tree rather than bypassing them.

```bash
(
set -e
git fetch origin
git switch staging
git merge --ff-only origin/staging
git merge --no-ff origin/codex/release-0.46.0 -m 'merge: C checkpoint into staging'
git diff --exit-code origin/codex/release-0.46.0 staging --
touch .momentum/merge-approved && git push origin staging
git switch main
git merge --ff-only origin/main
git merge --no-ff staging -m 'merge: staging into main for v0.46.0'
git diff --exit-code origin/codex/release-0.46.0 main --
touch .momentum/merge-approved && git push origin main
git tag -a v0.46.0 -m 'release: v0.46.0'
git push origin v0.46.0
gh release create v0.46.0 --title 'v0.46.0' --notes-file docs/migrations/0.46.md
)
```

Wait for build/helper/publish/smoke, then verify both distributions and all seven files, plus a
fresh install outside CI. A Linux install must resolve the matching helper. Update published
status only after that evidence, then proceed to D's release.

## Verification Evidence

Six new cases failed before implementation on the rejected plan key; ten now pass, and the
existing admission tests pass beside them. Full gate: **2,248 passed, 8 skipped, 24 deselected**, exit 0 with disposable PostgreSQL enabled;
lint/format/types clean. Ten anchored mutations bite. All ten new cases pass on a clean installed
0.46.0 wheel outside the checkout. All 165 package source files match the wheel. Schemas and
TypeScript contracts regenerate without drift. The kit wheel and sdist build.
