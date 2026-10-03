---
type: Reply
---

# Lane H — 0.47.0 candidate, H11-D

Not published. A stored description now reaches the existing agents-list reply, while absent
or null retains today's fallback and role instructions stay separate. See
[`0.47.md`](../../docs/migrations/0.47.md). The migration table records D as built; H6–H8 remain.
No new decision was needed and no product pin changed.

## Release order

Land and publish the independently frozen 0.45.0 and 0.46.0 candidates first, then
`codex/release-0.47.0`. Do not land the moving phase branch. Each checkpoint has its own version,
GitHub Release and publication verification; continued preparation does not mean publication.

## Owner commands

From a clean repository after the prior release is published. Equality checks stop this block
if upstream changed; re-gate the resulting tree rather than bypassing them.

```bash
(
set -e
git fetch origin
git switch staging
git merge --ff-only origin/staging
git merge --no-ff origin/codex/release-0.47.0 -m 'merge: D checkpoint into staging'
git diff --exit-code origin/codex/release-0.47.0 staging --
touch .momentum/merge-approved && git push origin staging
git switch main
git merge --ff-only origin/main
git merge --no-ff staging -m 'merge: staging into main for v0.47.0'
git diff --exit-code origin/codex/release-0.47.0 main --
touch .momentum/merge-approved && git push origin main
git tag -a v0.47.0 -m 'release: v0.47.0'
git push origin v0.47.0
gh release create v0.47.0 --title 'v0.47.0' --notes-file docs/migrations/0.47.md
)
```

Wait for build/helper/publish/smoke, then verify both distributions and all seven files, plus a
fresh install outside CI. A Linux install must resolve the matching helper. Update published
status only after that evidence, then proceed to H6's release.

## Verification Evidence

Five new cases failed before implementation. Six new cases and the existing wire listing tests
pass; seven targeted mutations bite. Full gate: **2,254 passed, 8 skipped, 24 deselected**, exit 0 with disposable PostgreSQL enabled;
lint/format/types clean. Six new cases pass on the clean installed wheel outside checkout, and
all 165 Python source files match it. Schemas and TypeScript contracts regenerate without drift.
The kit wheel and sdist build. Owner publication remains pending.
