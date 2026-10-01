---
type: Tasks
---

# Phase 64 — tasks

## G1 — an agent is a store row (D174)
- [ ] RED: no `StorePatterns`
- [ ] `StorePatterns` / `store_patterns(store, collection="agents")`, version-gated reload
- [ ] a malformed row is skipped and said, not fatal
- [ ] `load_pattern` and the packaged `library/` unchanged — asserted
- [ ] mutation-checked

## G2 — a mode names its agent (D175, D176)
- [ ] RED: `ModeSpec` has no `pattern`
- [ ] `ModeSpec.pattern`; `thread/start {agent}` overrides it
- [ ] an unknown name is **refused naming it**, never a silent `single`
- [ ] nothing named still gets `single` — asserted, so no existing composition moves
- [ ] measured: a store-backed agent's own system prompt is what the model was asked
- [ ] mutation-checked

## G3 — listing and introspection (D177)
- [ ] `agents/list` on the wire, beside modes/skills/rules/batteries/providers
- [ ] the resolved agent on the thread's description
- [ ] mutation-checked

## G4 — the two debts this phase carries
- [ ] TD-017 decided and applied (exclude `docs/**` from `ruff format`, or the alternative)
- [ ] ENH-026: `docs/for-a-product.md` to 0.43.0 — **including the `store/*` CRUD surface it has
      never described**, which is why lane P asked for a capability they already had

## G5 — close out
- [ ] the 0.43 migration note (named without its path — the document invariant refuses a path a
      document names that is not yet in the tree; TD-017)
- [ ] 0.43.0, the Linux helper in lockstep
- [ ] full gate; schemas + TS client regenerated if a contract moved
- [ ] `specs/status.md` own row
