---
type: Reply
---

# Lane H — 0.45.0 release candidate

Prepared on `phase-66-the-short-list`; **not published**. The owner must perform protected
landings, tag and publish before lane P changes its pin. See the migration note
[`0.45.md`](../../docs/migrations/0.45.md).

This checkpoint is **E**, plus the already gated unreleased phase 66 changes and the required
DDL-free PostgreSQL default. The release train continues with C as 0.46.0, then D as 0.47.0,
then individually confirmed H6–H8. No batch, no `absorb` or `offload_over` by symmetry.

E follows the existing approved design; **no new decision was needed**. The host pre-binds a
registry-resolved procedure only to its own model loop. On a CLI the requested pre-binding is
reported as `agent.skill`; skill choosing through the governed component remains available,
including its needs check. The procedure's text is not folded into a CLI's instructions.

**Named behaviour change:** PostgreSQL defaults to DDL-free runtime. Prepare under an owner role
before startup and after upgrades; explicit `prepared=False` retains legacy owner-role
self-preparation. This applies to the checkpointer as well as the three stores.

**The migration table changed:** E's built contracts now have their own row, C and D remain
explicitly unbuilt, and the default change is recorded. D184's standing requirement is met;
no Shadow code or product pin was changed by this lane.

The release note carries the three earlier migration cautions: validate `tools_offered` names,
set the governed Codex model explicitly, and handle `agent_unhonoured` in the chooser.

## Verification Evidence

Baseline: lint, format and strict types passed; 2,200 tests passed, 29 skipped, 24 deselected.
The new tests started red. Targeted new tests: 17 passed. PostgreSQL plus store tests on a
fresh disposable PostgreSQL 16 server: 37 passed, including restricted-role open and reopen.
Final gate: **2,238 passed, 8 skipped, 24 deselected**; lint/format/types clean. Twenty mutation
checks bite. The kit wheel and sdist build; a clean installation outside the checkout passes all 17
new cases. Schemas and TypeScript contracts regenerate without drift.

## Owner landing and publication commands

Run from the repository with a clean checkout. These commands verify the landing tree against
the gated feature branch before each protected push. If an upstream branch changed meanwhile,
stop and re-gate the resulting tree rather than bypassing equality.

```bash
(
set -e
git fetch origin
git switch staging
git merge --ff-only origin/staging
git merge --no-ff origin/codex/release-0.45.0 -m 'merge: phase 66 E checkpoint into staging'
git diff --exit-code origin/codex/release-0.45.0 staging --
touch .momentum/merge-approved && git push origin staging
git switch main
git merge --ff-only origin/main
git merge --no-ff staging -m 'merge: staging into main for v0.45.0'
git diff --exit-code origin/codex/release-0.45.0 main --
touch .momentum/merge-approved && git push origin main
git tag -a v0.45.0 -m 'release: v0.45.0'
git push origin v0.45.0
gh release create v0.45.0 --title 'v0.45.0' --notes-file docs/migrations/0.45.md
)
```

The GitHub Release publication triggers the workflow; a tag push alone does not. Wait for its
build/helper/publish/smoke jobs, verify both distributions and all seven files, then verify
`shadow-hdk==0.45.0` resolves in a fresh environment outside CI (Linux must resolve the matching
helper). Update the published status after that proof, then proceed to C as 0.46.0.
