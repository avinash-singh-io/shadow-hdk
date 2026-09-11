---
type: Phase
phase: 25
name: the-hosts-controls
epic: 0014-the-hosts-controls
status: in-progress
topics: [thread, turn, item, activity, modes, behaviour, approvals, store, terminology]
deps: [phase-24-the-skill-registry]
---

# Phase 25 — The host's controls

The harness was used for a day (`adhoc/studio-scenarios`) and then read against what Codex,
Claude Code, OpenCode and the Agent Client Protocol converge on (`planning/the-substrate.md`).
The ledger underneath us is richer than any of theirs — every step judged by effects, leased,
costed, with provenance — and the surface a host touches is poorer than all of them: no turn on the
record, nothing streams, a question that a host in another language cannot answer, a mode that is
a policy and nothing else, and the conversation itself living in an example.

This phase gives a host its controls, in the industry's words, without inventing a second engine.

**The words are the industry's** (§1.9 of the plan): `Thread`, `Turn`, `Item`, `delta`,
`ApprovalRequest`, `InputRequest`, `set_mode`/`set_option`, event kinds `reasoning` and `usage`.
`Lease`, the effect profile, the sink, provenance and posture stay — they are ours.

**A turn is a step.** A thread is a run; each turn is a step of that run; the provider's tool calls
are child steps under it (already so, by `parent`). Thread → Turn → Item is Run → Step → child
steps with no new concept, and the record gains turn boundaries for free.

**The activity is live, the record is complete** (principle 6). Partial thinking, partial text, a
running command's output, "composing" — on an ephemeral stream beside the record, never
checkpointed.

**A mode is policy + behaviour + presentation**, as data; `set_mode` on the thread changes it
mid-run; the provider file maps a behaviour to that CLI's flags.

**Approvals both ways.** An `ApprovalRequest` answered approve · deny · approve-and-add-rule (the
rule proposed through the sink); an `InputRequest` for the agent's own question to the person.

**Data changes live** (principle 10). A `Store` port is a source of every registry — modes,
behaviours, rules, skills, components-on, providers — refreshed at step boundaries; nothing a
product keeps in a database needs a restart.

## What this phase makes true

- A host renders a thread as turns of items with deltas, in the vocabulary every product uses.
- A person can switch the agent's mode, approve with a rule, and answer the agent's question —
  in-process now, over the wire in Phase 26 — with every one of those acts on the record.
- The studio consumes only the harness; the conversation primitive is the harness's.

## Out of scope

The wire's side of the handles and the store's CRUD as methods (26); web search, the facade (27);
compaction and memory (28); peers (29).
