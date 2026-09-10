---
type: History
phase: 5-the-recording-server
---

# Phase 5 — history

Append-only. Newest at the bottom.

| Entry type | Meaning |
|---|---|
| `[DECISION]` | a choice made, with what it rules out |
| `[ARCH_CHANGE]` | a structural change to the code or the specs |
| `[DISCOVERY]` | something the code or a library turned out to be |
| `[CORRECTION]` | a previous entry or plan proven wrong |

---

### [ARCH_CHANGE] 2026-09-10 — branched from Phase 4
Topics: branches, chain

`phase-5-the-recording-server` is cut from `phase-4-the-acp-bridge` at `a69135c`. The chain is
Phase 0 → 1 → 2 → 3 → 4 → 5.

### [CORRECTION] 2026-09-10 — a routed tool call is **controlled**, not observed
Topics: posture, controlled, observed, r9

`08` §4.6 says the recording server's calls carry *"posture: observed"*, and the instruction for this
phase repeated it. Building it makes the shorthand wrong, and the distinction `08` §9 R9 actually
draws says so:

> **Controlled versus observed** on every run and every act; only controlled satisfies
> consent-before-effect; observed renders as a degraded posture.

*Controlled* means **we gated it before it happened**. A call routed through the RecordingServer is
judged by our governance port and executed by our runtime — that is controlled in the strictest
sense available. Calling it observed would understate our own guarantee and, worse, would make a
gated call indistinguishable from an ungated one.

What is genuinely **observed** is the other thing a child agent does: its own unmediated work, which
we learn about from an ACP `session_update` *after* it happened. We did not consent to it; we found
out. That is the degraded posture R9 means.

So the line is not *parent versus child*. It is **gated versus merely reported**, and it happens to
cut through the middle of a child agent's behaviour: what it routes through us is controlled, what
it does natively is observed.

### [DECISION] 2026-09-10 — posture lives on `Provenance`, and only needs saying when it is `observed`
Topics: posture, provenance, kernel, d9

Three places it could live: an event field, the observation payload, or provenance.

The observation payload is untyped and ad-hoc. An event field would have to be added to several
events and would say the same thing repeatedly. **Provenance already answers "how did this come to
be here"**, which is exactly the question, and it already travels with every `Proposal` — the
carrier for *something happened and we are telling the host*.

`Provenance.posture` defaults to **`controlled`**, because everything the runtime invokes, it gated.
The exception is explicit: the ACP bridge stamps `observed` on a tool call it only heard about. A
default of controlled is the safe way round — an adapter that forgets to say produces a claim that
is true of everything the runtime does.

A kernel field is a contract change: every package takes a minor bump under D9, and it earns a row
under *Pins* on the board.
