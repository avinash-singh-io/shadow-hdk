---
type: History
phase: 25
---

# History — Phase 25

### [NOTE] 2026-09-12 — opened
Topics: thread, turn, item, activity, modes, approvals, store
Affects-phases: phase-25-the-hosts-controls
Affects-specs: none
Detail: Opened from `planning/the-substrate.md` (accepted 2026-09-12). Group 1 first: the industry's terms as one contract change, because every later group names things.

---

### [DECISION] 2026-09-12 — D61: the record speaks the industry's words

Topics: terminology, thread, turn, item, approval, input, reasoning, usage
Affects-phases: phase-25-the-hosts-controls
Affects-specs: architecture/runtime.md#modules, architecture/wire.md, decisions/index.md

Where the industry has a term, we use it; where the thing is ours — governance by effects, the
lease, the sink, provenance, posture — we keep the word and document the mapping; invented names go
(`planning/the-substrate.md` §1.9). Applied as one contract change, 0.21.0: event kinds
`reasoning` (was `reasoned`), `usage` (was `spent`), `approval_requested` (was `asked`, carrying
component and inputs from D59), and a thirteenth, `input_requested` — the agent's own question to
the person, which Codex, Claude Code and OpenCode all have as an item and ours wrote into prose.
Observations `ApprovalRequest` and `InputRequest`. The projection a host renders is an `Item`
(`runtime.items`; the kernel's plan unit stays a `Step`, a standard word too). The host's handle
is `Approvals`; its answers are `Approve`, `Deny`, `ApproveAndAddRule` — Codex's
accept · decline · acceptWithExecpolicyAmendment, Claude Code's "yes, and don't ask again" — and
`RunContext.request_approval` turns them into the loop's judgement. The wire's `step` notification
is `item`; `context.reasoned`/`context.ask` are `context.reasoning`/`context.request_approval`.

Measured on the way: a blind sweep renamed two things that were *not* the vocabulary — the
LangGraph state channel `spent` and a test's plain-English "asked" — and the suite caught both
(spend across a park, a parametrize name). The state channel keeps its name: it is the
checkpoint's, not the record's.

*Why:* a host reads the record without a glossary, and a client developer who knows Codex or
the Responses API already knows ours.

---
