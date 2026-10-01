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
### [ARCH_CHANGE] 2026-10-02 — the narrowing lives in two catalogues, by one derivation
Topics: tools-offered, narrowing, offer, registry, catalogue
Affects-phases: none
Affects-specs: none
Detail: BUG-230 could have been closed in `AgentSession.catalogue` alone, and that would have left
the claim false for every provider a product actually runs: Claude Code and Codex are handed no
catalogue — they **list the registry over MCP** and decide for themselves. So the kernel gains one
pure derivation (`narrowed`/`unanswered`) and it is applied twice: in the in-process catalogue, and
on the offer that answers a CLI's listing, through a settable `narrow_to` that the conversation sets
at open and again at every `set_mode`. Settable rather than a construction argument the way
`withhold` is, because the narrowing travels on the mode and a mode changes mid-thread. `Narrowing`
is a separate `runtime_checkable` Protocol rather than a method on `Offer`, so a host that wrote its
own offer against that port still satisfies it (D14).

---

### [DISCOVERY] 2026-10-02 — the `tools_offered` union in `unmapped_behaviour` was dead code
Topics: honesty, mutation-testing, tools-offered
Affects-phases: none
Affects-specs: none
Detail: `unmapped_behaviour` unioned `"tools_offered"` into its `mapped` set, which read as *this is
delivered elsewhere*. A mutation deleting the union **survived**: the function walks five field names
and `tools_offered` is not one of them, so the union could never change an answer. The lie was not
merely false, it was inert — and the test that first covered it passed vacuously. Both were fixed:
the dead union is gone, and the test now pairs a narrowing with a `temperature` the CLI genuinely
cannot take, so exactly one name comes back and it is the other one. Two further equivalent mutants
(redundant empty-offered guards) were resolved by deleting the guards rather than by inventing tests
that could not distinguish them.

---
