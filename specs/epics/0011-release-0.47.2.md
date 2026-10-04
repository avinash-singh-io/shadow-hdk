---
type: Reply
---

# Lane H — 0.47.2 candidate, H7 / BUG-239

Not published. Native interruption now sends the configured control line and drains the old
terminal frame before the next prompt, preserving the process without leaking old activity.
See [`0.47.2.md`](../../docs/migrations/0.47.2.md). Live checked on Claude Code 2.1.187.

## Release order

Publish frozen 0.45.0, 0.46.0, 0.47.0 and 0.47.1 first, one at a time, then
`codex/release-0.47.2`. Do not land the moving phase branch. H8 remains a separate release.

## Owner commands

From a clean repository after the prior release is published. Equality checks stop this block
if upstream changed; re-gate the resulting tree rather than bypassing them.

```bash
(
set -e
git fetch origin
git switch staging
git merge --ff-only origin/staging
git merge --no-ff origin/codex/release-0.47.2 -m 'merge: H7 checkpoint into staging'
git diff --exit-code origin/codex/release-0.47.2 staging --
touch .momentum/merge-approved && git push origin staging
git switch main
git merge --ff-only origin/main
git merge --no-ff staging -m 'merge: staging into main for v0.47.2'
git diff --exit-code origin/codex/release-0.47.2 main --
touch .momentum/merge-approved && git push origin main
git tag -a v0.47.2 -m 'release: v0.47.2'
git push origin v0.47.2
gh release create v0.47.2 --title 'v0.47.2' --notes-file docs/migrations/0.47.2.md
)
```

Wait for build/helper/publish/smoke, then verify both distributions and all seven files, plus a
fresh install outside CI. A Linux install must resolve the matching helper. Update published
status only after that evidence, then proceed to H8's release.

## Verification Evidence

Two cases failed before implementation, separately proving the missing line and stale result.
Four final cases pass, including completion during the interrupt write; all 76 JSONL cases pass.
Eight targeted mutations bite. Full gate: **2,264 passed, 8 skipped, 24 deselected**, exit 0 with
disposable PostgreSQL enabled; lint/format/types clean. Four new cases pass against a fresh installed
wheel outside checkout. All 165 Python package sources and the shipped provider record match it.
Kit wheel/sdist build; schemas and TypeScript regenerate without drift.

Live on Claude Code 2.1.187, both source and installed artifact: interrupt accepted, same process
and provider session retained, following turn returned SECOND_OK without failure. Old thinking
and activity are discarded at the cancelled boundary; providers without a native line keep the
close/reopen fallback. Owner publication remains pending.
