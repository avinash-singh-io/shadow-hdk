---
type: Config
---

# Project Config

> Recipes read these at execution time; missing values fall back to npm/GitHub defaults. Edit freely.
> Confirmed at founding, 2026-09-10.

| Key | Value |
|-----|-------|
| language | python |
| framework | langgraph |
| test_command | uv run pytest |
| build_command | uv sync --all-packages --all-extras |
| publish_target | pypi |
| git_forge | github |
| release_command | gh release create |
| release_flow | tag-and-publish |
| end_state | merge-after-yes |
| branch_flow | staging, main |
| protected_branches | staging, main |
| review_min_approvals |  |
| review_self_approval |  |
| presence_idle_seconds |  |
| presence_offline_seconds |  |

## Notes

### Branch flow: `phase → staging → main`

`staging` is the permanent integration branch; every phase lands there with the owner's single-use
approval sentinel (Rule 6). `main` is touched only at a release: a promotion from staging, tagged.
Both are protected by momentum's hook floor whatever this file says.

### Release flow: `tag-and-publish`

The project is MIT-licensed and v0.30.0 is authorized for publication. A GitHub release for the
matching `vX.Y.Z` tag triggers the publish workflow, which builds, checks, publishes to PyPI and
smoke-tests a fresh installation.
