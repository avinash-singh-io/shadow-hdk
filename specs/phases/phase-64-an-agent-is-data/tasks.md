---
type: Tasks
---

# Phase 64 — tasks

## G1 — an agent is a store row (D174)
- [x] RED: no `StorePatterns`
- [x] `StorePatterns` / `store_patterns(store, collection="agents")`, version-gated reload
- [x] a malformed row is skipped and said, not fatal
- [x] `load_pattern` and the packaged `library/` unchanged — asserted
- [x] mutation-checked

## G2 — a mode names its agent (D175, D176)
- [x] RED: `ModeSpec` has no `pattern`
- [x] `ModeSpec.pattern`; `thread/start {agent}` overrides it
- [x] an unknown name is **refused naming it**, never a silent `single`
- [x] nothing named still gets `single` — asserted, so no existing composition moves
- [x] measured: a store-backed agent's own system prompt is what the model was asked
- [x] mutation-checked

## G3 — listing and introspection (D177)
- [x] `agents/list` on the wire, beside modes/skills/rules/batteries/providers
- [x] the resolved agent on the thread's description
- [x] mutation-checked

## G4 — the two debts this phase carries
- [x] TD-017 decided and applied (exclude `docs/**` from `ruff format`, or the alternative)
- [x] ENH-026: `docs/for-a-product.md` to 0.43.0 — **including the `store/*` CRUD surface it has
      never described**, which is why lane P asked for a capability they already had

## G5 — close out
- [x] the 0.43 migration note (named without its path — the document invariant refuses a path a
      document names that is not yet in the tree; TD-017)
- [x] 0.43.0, the Linux helper in lockstep
- [x] full gate; schemas + TS client regenerated if a contract moved
- [x] `specs/status.md` own row
