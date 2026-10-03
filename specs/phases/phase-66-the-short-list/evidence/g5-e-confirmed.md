---
type: Evidence
phase: phase-66-the-short-list
group: G5-E
---

# E — agent-row skill binding, confirmed before implementation

Read on 2026-10-04 at branch head `08437fe`.

The pattern has no skill field; the loader rejects it, causing a store source to skip that row.
The host constructs a model agent with a pattern alone. The model agent already accepts a skill,
and its loop checks dependencies before its first model call and appends the procedure to the role.
The missing path is stored name → registry resolution → existing model-agent binding.

The approved audit says CLI providers get their own skills only. Follow that wording: validate the
stored name on every provider path, bind on the kit-owned model loop, and report `agent.skill` in
unmapped behaviour when another provider owns the loop. Do not silently fold a procedure into a CLI
prompt and call that binding: the kit would not enforce that procedure's needs there. An optional
clarification was presented to the owner; this is the documented default from the approved audit.

D190: a coding tool, a support desk and a research assistant would each use this. A procedure and
its declared dependencies are content supplied by the host; resolving an opaque name and reporting
unsupported execution are generic mechanisms. No operation names are added to kernel or runtime.

The first release carries E plus the previously gated unreleased phase work and the mandated
DDL-free PostgreSQL default change. C, D and H6–H8 belong to later releases, one item each.

## Resolved — 2026-10-04

The owner relayed the open question back, with the recommendation to bind on key-backed models and
report the binding as unhonoured on CLI runs. That is the documented default above, so it stands and
E needs no redesign. Confirmed against the tree rather than from the audit's wording alone:
`_agent_named` resolves the stored name on every provider path and binds the resolved procedure only
where the kit owns the loop, `_agent_carries` reports `agent.skill` where it does not, and
`_open_provider` folds that report into the session's unmapped behaviour. A mutation binding `None`
on the model path kills three of the eleven assertions.

One clarification belongs with the decision, so a later reader does not close a gap that is not one.
A skill is **not** unavailable to a CLI. `use_skill` is registered as a component (D55) and reaches
an in-process agent, an agent across the wire and a CLI by subscription alike, and D17's check runs
there against `visible()` exactly as it does before the kit's own first turn. What a CLI cannot be
given is a procedure **pre-bound** by the host, because pre-binding is a pre-first-turn act and a
provider that owns its loop owns that turn. So the line is not model-versus-CLI, it is binding
versus choosing: the host binds where the kit has a first turn to check against, and everywhere else
the model still chooses, checked. This is why folding the procedure into a CLI's instructions would
be wrong rather than merely incomplete — it would deliver a procedure's text while skipping the
check that `needs` exists for, which is the silent-drop shape the phase was opened to remove.

## Test-first and mutation evidence

The eight original new E cases failed before implementation because the stored skill row was
rejected. Reporting was separately checked red with the fold absent (one failed, two passed),
then restored. Seventeen new E/default cases pass. The dependency refusal and actual procedure
text delivery both bite when removed. A direct Pattern default assertion was added after a
mutation exposed the missing coverage; that mutation now bites. The internal pool default was
redundant because every public adapter explicitly supplies the flag, so it was deleted instead
of inventing a test of a default no runtime path uses.
