---
type: Handoff
to: lane P
from: lane H
date: 2026-10-02
---

# Reply to the harness audit of 2026-10-02 — Wave 1 is done

Pin **`shadow-hdk==0.44.0`** once it is published. Until then `0.43.0` is current and real.

## First, two corrections to the audit

**0.43.0 is tagged, merged and published.** The warning that it *"exists only on lane H's local
staging branch, untagged and unpublished"* was true when you wrote it and is not now: `v0.43.0` is on
`origin`, merged to `main`, and `shadow-hdk==0.43.0` resolves from PyPI. So **H9 is closed** — its
release half yesterday, and its other half (*"File A1–A8 and the other untracked gaps"*) today:
BUG-230 through BUG-234 and TD-020 are in the backlog, each with the file and line that confirms it.

**You were right about one thing in H9**, though: `specs/status.md` still headlined v0.42.0. That was
our defect and it is fixed.

## Your ask back: A1–A8 confirmed against the code

You asked us to confirm them before fixing, *"because they come from reading the source, not from
running it."* That was the right ask. **A1–A5 are all real**, and three of the five are ours — from
our own phases 62 and 64, which means we shipped the claim and the defect together.

| | where it was confirmed |
|---|---|
| A1 / H1 | `kernel/providers.py:377,438` · `adapters/jsonl/transport.py:95` · `adapters/agent/component.py:327` |
| A2 / H2 | `adapters/langchain/model.py:101` |
| A3 / H3 | `adapters/agent/component.py:182` |
| A4 / H4 | `adapters/jsonl/session.py:32,174` |
| A5 / H5 | `runtime/threads.py:684`, and `ThreadRecord` having no such field |

A6–A8 (H6, H7, H8) were **not confirmed and not built** — Wave 1 was scoped to the five above plus
H37. They remain open and unexamined; treat their *Kit today* column as still unverified.

## What 0.44.0 does

`docs/migrations/0.44.md` is the full note. The five in brief:

**H1 — `tools_offered` narrows.** Worth knowing *where*: there are two catalogues. A key-backed model
is handed a list; Claude Code and Codex are handed nothing and **ask** the registry over MCP. Fixing
only the first would have left the claim false for the providers you actually run, so both narrow, from
one derivation. A narrowed name is also not callable, so a CLI holding a listing from before a
`set_mode` cannot reach past it. A name no component answers to is refused, naming it.

→ **Your C5 note was right.** The tool limit you planned as product work can now be the kit's. If you
built your own enforcement, you can drop it.

**H2 — a key-backed model honours the mode's `model`.** One host, a cheap model for one mode and a
strong one for another, now works. One caveat you need: if you build your `LangChainModel` with
`over(chat)` rather than from a spec, it cannot be re-specified, so it reports `selects_model` false
and `unmapped_behaviour` names `model`. That is new information, not a new limitation — it was being
dropped silently before.

**H3 — a key-backed thread remembers its turns.** You guessed in your own C-stage notes that your
model source might already be passing the history itself; worth checking, because if you are, you are
now paying for it twice. **The transcript is unbounded** (ENH-052). That is deliberate and it is a real
edge: fitting one to a model's window is a budget and a compaction, which are your H33 and H34 and are
not built. A long thread will reach the window.

**H4 — no 10-minute cliff.** The fix is not a bigger number, it is a different measurement: the
ceiling is now the **gap between frames**, so a CLI that keeps streaming is never given up on however
long the run takes. Default 1800 seconds of silence, and a mode may set `behaviour.silence_seconds`.
Time we spend answering the provider's own call — your policy's judgement, your component, a person's
approval — is given back to it, so a twenty-minute approval no longer fails the turn.

→ **Your question "does a Claude Code turn longer than 10 minutes fail in production?"** — on 0.34.1,
which 0.6.10 pins: **yes**, if the turn's total exceeded 600s, and yes if a person took that long to
approve. Both are fixed in 0.44.0 and in nothing earlier.

**H5 — an agent survives a mode switch and a resume.** `ThreadRecord` gained `agent` and
`agent_override`. If you map the record to columns, read `version` first as you already do; an older
record reads them empty, meaning *no agent in particular*.

## H37 — still not measured, and now it says so

The Codex fold has never run end to end. This laptop's Codex refuses every model offered it
(`gpt-6.1-sol`, `gpt-5-codex`, `gpt-5`, `gpt-5.1-codex-max`, `o3` — *not supported when using Codex
with a ChatGPT account*), so the turn fails before anything can be observed and the two live tests
skip. **The skip now names the account needed and what the measurement would prove**, so whoever has a
working account can close it without reading a backlog row. Filed as TD-020.

The two Claude Code legs were run live for this release and pass: with `--system-prompt` removed from
its record the fold is the only way in, and the paired negative shows the sentinel is not something the
model says anyway. So the mechanism is measured; the provider it exists for is not.

**This is the one Wave 1 item we cannot close ourselves.** It needs the account.

## H41–H43, noted and not scheduled

The three you added later — delegation under the host's ceiling, fan-out limits, agents made at run
time — are P2 and in wave 4, and we have not started them. Three of their *Kit today* entries say
"unconfirmed" or "not known" (whether a delegating parent waits, whether any depth or concurrency cap
exists, whether an agent can be defined at run time). **We can confirm those three against the code
cheaply** if that would help you prioritise; say the word.

One thing to flag: these are new capability, not corrections, and they are the clearest case yet for
the native line rather than this one. Building a workflow runtime and a delegation model here would be
the duplication you have been trying to avoid.

## What we did not do, and why

The owner's decision of 2026-10-02 was **Wave 1 only**. Everything else in the forty-three items is
untouched and named in the phase overview's *Out* so nobody later reads it as an oversight: H6–H8,
H10–H36, H38–H43. In particular **H10 is still not written** — D153 requires every bridge phase to say
what moves to Shadow, and none has, including this one. You are right that it is a gap; it is a
decision about the native line's scope rather than work in this repository, and it needs the owner.

## Your other four asks

| you asked | answer |
|---|---|
| Where do the vault and the egress proxy live? | The owner decided: mechanism in the harness behind a port, storage per deployment. Not built here — H29/H30 are wave 3 and outside Wave 1 |
| Was the SKILL.md parser worth it? | You said yes, and that H35 is next. Noted, not scheduled |
| Who carries lane H's row on the board? | Lane P, one line per release. Agreed |
| Do you rely on `docs/for-a-product.md`? | Kept current with this release, including the five corrections above |
