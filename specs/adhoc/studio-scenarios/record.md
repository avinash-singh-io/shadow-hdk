---
type: Ad-hoc Record
---

# Ad-hoc Work Record: studio-scenarios

> **Type**: quick-task — the studio driven like a person would drive it, and what that found
> **Created**: 2026-09-12
> **Branch**: `feat/studio-inline-and-scenarios`
> **Backlog**: BUG-023 … BUG-029 closed; ENH-006, ENH-007, ENH-008 filed
> **Status**: shipped

The owner asked two things. First, that the studio's page show the agent's trace the way the
serious agent UIs do — inline in the conversation, in the order it happened, not in a column of
its own — and that the workspace concept be explained from first principles. Second, that the
harness be *used*: real tasks, through the studio, on the owner's subscription, to see what works,
what does not, and what should.

## The page

An assistant turn is a sequence of parts in time order — reasoning, a tool call with its result
folded under it, a question with its buttons, the text — inside the conversation. Sub-agents nest
under the step that spawned them. The side panel is for the *environment*: the root's files, the
changed ones marked. This is what the Vercel AI SDK formalised as `UIMessage.parts`, what Claude
Code prints, what Cursor and ChatGPT's agent mode render; the runtime's `Step` projection is
already that shape, so the change was rendering. Markdown answers (fences, lists, tables), the
page read per request so a person can iterate on it while the conversation stays open.

## The workspace, from first principles

*Where do effects land?* The environment: a root, a mode, and proven isolation. "Workspace" now
names exactly three things — the root the environment confines to, the scope name `workspace` in
an effect profile, and the cwd the provider CLI is launched in. The CLI runs *outside* the sandbox
(it needs the network for the model) with its own tools withheld; every tool it calls goes through
the authenticated registry socket into this run's environment, and the OS enforces the mode.
Widening is an Ask. The studio's file panel is the root — the legitimate side panel.

## Five scenarios, on the owner's subscription

| # | Task | Mode | Turns · cost | Outcome |
|---|------|------|-------------|---------|
| 1 | a `wc` CLI with unittest tests, run and fix | workspace-write | 1 · 46¢ | 24 tests green first run; six governed calls; temp files landed in the root (`TMPDIR`) |
| 2 | a playable Snake game in one HTML file, syntax-checked | workspace-write | 1 · 168¢ | 15.8 KB game written, a headless harness written and run by the agent, cleaned up; **played in the browser** — start, steer, wall death, restart. A write to `/tmp` was **denied by seatbelt** and the agent recovered |
| 3 | refactor a drifted mini-repo, add the test that would have caught it, commit | workspace-write | 3 · 182¢ | found the `>` vs `>=` drift with a table, **asked before deciding** as instructed, refactored, proved the new test fails on the old code, **could not commit** — BUG-023 — then committed once fixed |
| 4 | analyse a CSV, install pandas if needed, write a report | full | 1 · 86¢ (after two dead runs) | every write asked about **with the tool and its arguments** (after BUG-026); `pip install` **refused** by the person; the agent fell back to the stdlib and found both planted anomalies and two real artefacts of the generator. The first two attempts killed the conversation — BUG-027, BUG-028 |
| 5 | add a `.gitignore` and run the tests | read-only | 1 · 47¢ | conversation opens (after BUG-029); tests ran; the write was **denied by the OS at two doors** and the agent said so, offering the content instead |

## What worked

- Governance by effects held every time: writes outside the root denied by the OS, not by string
  checks; the network denied inside the sandbox; the CLI's own tools refused by the CLI.
- The record is complete and honest: every call, its inputs, its result; refusals as refusals.
- The agents were honest about what they could not do — never once claimed a write that was denied.
- Asking before deciding, when instructed, produced exactly one good question.
- Human-in-the-loop end to end, once the questions said what they were about and the relay waited.

## What did not, and was fixed

BUG-023 (`/dev/null`), BUG-024 (parallel calls born exhausted), BUG-025 (an exception group named
nothing), BUG-026 (a question named nothing), BUG-027 (a dead connection ended the conversation),
BUG-028 (the relay's thirty-second timeout), BUG-029 (read-only refused the conversation). Every
one measured live first, reproduced under a test second, fixed third.

## What should be different, and is filed

ENH-006 a scratch directory in read-only; ENH-007 nothing on screen while a long tool call is
composed, and no `Reasoned` at all unless the model chooses to think; ENH-008 the CLI's refused
attempts on its own tools are invisible on the record.

## Log

- 2026-09-12 — page rebuilt inline; scenarios 1–5 driven; seven bugs found and closed; 0.20.0.

## Decisions taken in this round

### [DECISION] 2026-09-12 — D59: a question says what it is about

Topics: ask, consent, asked-event, questions, bug-026
Affects-phases: none
Affects-specs: architecture/runtime.md#the-governed-step, architecture/wire.md

A step is judged before it is invoked, so an `Asked` carried the policy's sentence and a step id
and nothing else, and a person answering the studio's first live question could not see whether
they were allowing `read_file sales.csv` or `pip install pandas`. Consent to something unseen is
not consent (D38). `Asked` — the event and the observation — carries `component` and `inputs`;
the executor fills them on the governance path, an agent passes a child's on through D57, the
RecordingServer names the call itself on the live path (D58), and `about` crosses the wire with
`context.ask`. A question whose asker stopped waiting is announced (`next_withdrawn`) so a host
takes its buttons away. Kernel contract change: 0.20.0.

*Why:* an approval is a decision about an act; the act has to be on the card.

---

### [DECISION] 2026-09-12 — D60: a connection's death is that connection's problem

Topics: registry, socket, relay, task-groups, bug-027, bug-028
Affects-phases: none
Affects-specs: architecture/runtime.md#the-socket

The registry serves many connections over one listener, and one connection dying — the CLI
killing its relay while a result was being written to it — raised out of that connection's task
group, through the listener's, into the step holding the conversation, which ended. A connection
handler contains its own death (broken, closed, reset, end of stream) and the listener goes on
serving; anything that is not the wire going away still propagates, and a test says so. And the
relay itself must never be the thing that dies while a person thinks: the timeout
`create_connection` leaves on the socket is cleared once connected, and the CLI's own tool-call
clock is set to a day.

*Why:* the conversation is the unit of value; a socket is not.

---
