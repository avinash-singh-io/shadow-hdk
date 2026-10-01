---
type: History
phase: phase-65-the-claims-are-true
---

# Phase 65 history

### [SCOPE_CHANGE] 2026-10-02 — Wave 1 only, from a forty-item audit
Topics: audit, scope, native-line
Affects-phases: none
Affects-specs: specs/phases/phase-65-the-claims-are-true/overview.md
Detail: Lane P's audit of 2026-10-02 lists forty items. The decision taken was to build only its
A-group — claims this kit already makes that are not true — on the ground that new capability
belongs to the native line rather than to a maintenance-supported implementation. Every other item
is named in the overview's **Out** so no later reader mistakes it for an oversight.

---

### [DISCOVERY] 2026-10-02 — five claims confirmed false against the source, three of them mine
Topics: honesty, behaviour, tools-offered, model-port, conversation, timeout, agents
Affects-phases: none
Affects-specs: specs/backlog/backlog.md
Detail: BUG-230 through BUG-234 filed after reading the source rather than trusting the audit —
the audit itself asked for that. `tools_offered` narrows nothing while two fields report it
honoured (phase 62, mine); `request.model` is discarded by the only real `ModelPort` while phase 62
claimed otherwise (mine); a key-backed conversation opens fresh every turn with nothing saying so;
a 600s ceiling counts a person's thinking time and blames the provider; and phase 64's agent
selection survives neither `set_mode` nor a resume (mine, and it bounds what 0.43.0 delivered).
TD-020 records the one Wave 1 item that cannot be closed here — Codex's fold is unmeasurable on
this laptop's account.

---
