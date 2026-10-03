---
type: Reply
---

# Lane H — 0.47.1 candidate, H6 / BUG-238

Not published. Mode fragments now decode before the shared prompt assembler reads them.
The crash is confirmed; the audit's missing-wire-path claim is not: existing store/put already
carries these rows. See [`0.47.1.md`](../../docs/migrations/0.47.1.md).

## Release order

Publish frozen 0.45.0, 0.46.0 and 0.47.0 first, one at a time, then `codex/release-0.47.1`.
Do not land the moving phase branch. H7 and H8 remain separate releases.

## Owner commands

From a clean repository after the prior release is published. Equality checks stop this block
if upstream changed; re-gate the resulting tree rather than bypassing them.

```bash
(
set -e
git fetch origin
git switch staging
git merge --ff-only origin/staging
git merge --no-ff origin/codex/release-0.47.1 -m 'merge: H6 checkpoint into staging'
git diff --exit-code origin/codex/release-0.47.1 staging --
touch .momentum/merge-approved && git push origin staging
git switch main
git merge --ff-only origin/main
git merge --no-ff staging -m 'merge: staging into main for v0.47.1'
git diff --exit-code origin/codex/release-0.47.1 main --
touch .momentum/merge-approved && git push origin main
git tag -a v0.47.1 -m 'release: v0.47.1'
git push origin v0.47.1
gh release create v0.47.1 --title 'v0.47.1' --notes-file docs/migrations/0.47.1.md
)
```

Wait for build/helper/publish/smoke, then verify both distributions and all seven files, plus a
fresh install outside CI. A Linux install must resolve the matching helper. Update published
status only after that evidence, then proceed to H7's release.

## Verification Evidence

Five new cases failed before implementation. All six new cases and 118 mode cases pass after it;
ten targeted mutations bite. Full gate: **2,260 passed, 8 skipped, 24 deselected**, exit 0 with
disposable PostgreSQL enabled; lint/format/types clean. Six new cases pass against a fresh installed
wheel outside checkout; all 165 Python source files match it. Kit wheel and sdist build; schemas
and TypeScript contracts regenerate without drift. Owner publication remains pending.
