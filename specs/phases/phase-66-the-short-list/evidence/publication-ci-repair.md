# Release preflight repair — 2026-10-04

Owner authorized all six landings and publications in this chat. Before the first tag,
GitHub CI exposed a test dependency on a locally installed vendor CLI. The original wire test
fails under a `ready` guard that refuses external discovery (1 failed in 0.52s), matching all
five clean CI test runners. Handing the host a minimal CLI port preserves the no-model path
while removing machine-specific provider discovery. The guard plus the complete wire file
passes: 9 passed in 0.94s. Both existing assertions were mutation-checked with source caches
cleared and bytecode writes disabled: empty `agent_unhonoured` and falsely reported `agent`
each produce 1 failed, without a timeout. Ruff lint and format checks pass.

Production/package sources are unchanged from each frozen candidate. Subsequent merged trees
retain this single test repair and this evidence file; compare every other path to its frozen
candidate, then rerun the full merged-tree gate and wait for CI before tagging. This is a
release verification repair, not an additional shipped feature.
