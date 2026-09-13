---
type: Ad-hoc Record
---

# Ad-hoc Work Record: 2026-09-13-publish-to-pypi

> **Type**: quick-task
> **Created**: 2026-09-13
> **Branch**: chore/publish-to-pypi
> **Backlog**: none
> **Status**: shipped (the first publish waits on the owner's token and word)

## Current Behavior

The eighteen distributions build and install from wheels, but nothing publishes them: no
package carries the URLs or classifiers a PyPI page shows, and no workflow uploads.

## Expected Behavior

`[project.urls]` and classifiers on every package (measured in the built METADATA); all 36
artefacts pass `twine check`; `.github/workflows/publish.yml` builds the eighteen, refuses a
release whose tag is not the packages' version, publishes to TestPyPI on demand or to PyPI on a
published release, and smoke-installs from the index into a fresh venv — imports, and
`shadow-hdk serve --stdio` answers `initialize`. Credentials are repository secrets the owner
sets; the tree carries none. README gains an *Install* section.

## Unchanged Behavior

No code, contract or port changes: 0.26.1 is a patch of metadata and CI. The existing `ci.yml`
is untouched.

## Verification Evidence

- `uv build --all-packages` → 36 artefacts; `uvx twine check dist/*` → 36 PASSED
- kernel wheel METADATA: `Project-URL` ×4, `License-Expression: MIT`, 7 classifiers, `Description-Content-Type: text/markdown`
- `publish.yml` parses (jobs: build, publish, smoke); the version gate and the fresh-venv smoke are the workflow's own steps
- gate on the branch: ruff 0 · format 0 · mypy 0 · `1413 passed, 2 skipped, 12 deselected`
