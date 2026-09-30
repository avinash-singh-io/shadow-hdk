---
type: Handoff
---

# For lane P, from lane H — the desktop walk answered (2026-09-30)

Against `intent-ecosystem/handoffs/harness-from-the-desktop-walk-2026-09-30.md`, items 1–5
(`88dd4d8`) and 6–10 (`f709b19`). Every item is answered; four defects and one enhancement shipped.

## Pin this

| | |
|---|---|
| **`shadow-hdk==0.36.0`** | the pin to take. Everything below is in it. |
| 0.34.2 | the P0 and the parked wording (a patch — no contract moved) |
| 0.35.0 | ENH-041, the read-class file tools (a minor — additions, a *Pins* row) |
| 0.36.0 | `edit_file` and `move_file` — the edit half of item 4 (a minor — additions, a *Pins* row) |

All three are published complete on PyPI — **both distributions, all seven files each**. The Linux
helper moves in lockstep, so `shadow-hdk==0.36.0` resolves on `manylinux2014` x86_64 **and** aarch64,
which we verified from outside CI rather than assuming. Your production Linux is covered.

*(If you already pinned 0.34.2 in the hours after we published it: it was briefly unresolvable on
Linux, because its kit wheel went up from a laptop while GitHub Actions was down for billing and
the helper could not follow. That is fixed — 0.34.2 and 0.35.0 are both complete — and the workflow
now passes `--check-url` so a half-published release finishes on a re-run instead of dying on the
files already there.)*

**In the order you asked for.**

---

## 1. P0 — the relay's path with a space. Fixed; 0.34.2.

Confirmed exactly as you described, and the kit-only reproduction is now a test.

**The rule: an address is a command, never a command line.** Nothing splits `ToolSource.address`
on any transport — Claude Code's JSON `--mcp-config`, Codex's `-c` overrides, ACP's `session/new`.
Each has a test with `/Applications/Intent Studio.app/…/shadow-hdk-registry` in it
(`tests/adapters/test_the_relay_reaches_the_child.py`), including the launch argv end to end.

On your two options: **treat `address` as a single path**, not a command/argv pair on `ToolSource`.
Nothing in the kit ever put arguments in an address — the only producer is `relay_source`, which
names one path — so the split was accidental, and removing it is a bug fix rather than a contract
change. That is what let this ship as a patch today instead of a minor next week. The vector shape
is filed as **ENH-040** and will land the day something needs arguments; putting it in now would
have cost you a week and bought nothing.

Also taken: **the relay is resolved beside the running interpreter before `PATH`.** A console
script is installed next to the interpreter of the environment it was installed into, so that is
the kit's own copy by construction; a `PATH` lookup answers for whatever environment the *service*
was started with. `PATH` and the bare name remain as fallbacks, so a source tree is unaffected.

### One more, found while writing your OpenCode leg — BUG-227

`adapters/acp/agent.py::mcp_servers_from` built its MCP entry with `env=[]`. The registry's port and
token are minted per thread and live **only** on the `ToolSource`; they are in no process
environment. So the relay OpenCode launched started and printed
`SHADOW_HDK_REGISTRY_PORT is not set to a port; nothing to relay to` — a governed OpenCode with no
tools, the same outcome as yours, for an entirely independent reason. Fixed in the same patch.

Worth saying plainly: **your release check is the one that would have caught both.** No developer
tree has a path with a space in it, and nothing in our suite launched ACP for real. Your "tested as
installed" check closes a gap on this side too.

---

## 2. P1 — the parked note. Fixed; 0.34.2. And one correction.

**The correction first, because it changes your fix.** On the key-backed path the model did not
echo anything. `adapters/agent/model.py` took the note written *for the agent* and used it as the
**turn's own text**, so what you saw was the kit speaking, not DeepSeek repeating. Both halves are
fixed, but the one that produced your screenshot was ours outright.

- The agent-facing note is now a fact about the call with no second person and no order in it. A
  regex test pins the property, not the wording, so nobody can quietly put an imperative back.
- A parked turn's text is now the kit's plainest description of why it stopped.
- **`Turn.stop_reason == "parked"` is the signal to key on.** It was already there.

**Does a key-backed loop need to ask the model for parting words after a park?** No. It never did —
the turn ends at the park, and always has. Speak in your own words; neither sentence the kit writes
is meant for a person to read.

---

## 3. Question — a key-backed model's parked turn. **(b) works today, and so does (a).**

**Settling does not go through the provider.** `settle(handle, answer)` wakes the run that parked
from the **checkpointer**, and the act resumes at the step it stopped on. The provider is never
consulted — which is why a key-backed model, with no session to reopen, does not need one. The
record is its memory (D98), and that is enough.

So your thread-for-the-turn is fine as a shape. `tests/runtime/test_a_key_backed_models_park_settles_after_a_restart.py`
is the proof, on sqlite: a `ModelAgent` parks, **the thread is closed**, a fresh `Thread.resume(id)`
finds the question under the same handle, `settle` runs the act once, and the model is told at its
next turn what became of the call. (a) works for the same reason; choose it for process lifetime,
not because approvals need it.

**Two things to get right, and the first is the likely cause of your 404s:**

- **Pass `approvals=` and a durable `checkpointer=`.** With no `Questions` handle, a mode that asks
  is answered by a refusal saying nobody was there — consent nobody gave is not consent — so a
  thread opened without it sees *silent refusals, not parks*, and nothing ever lands on `pending`.
  This is exactly the shape of "the worker finds nothing pending and tells the Run `succeeded`".
  Check that first before changing your architecture. With an in-memory checkpointer the question
  survives on the record and the run to resume does not — which fails later and worse.
- **Nothing extra for a stateless provider's resident thread.** No memory to set, no transcript to
  reseed. `_seed_if_fresh` already tells a fresh session the kept turns after a `fork` or
  `rollback` (0.34.1), and that is the only seeding there is.

(c) is not recommended and we are not moving back toward it.

---

## 4. Capability — the governed toolset. Agreed, split in two, and here is the sequencing.

You are right, and the framing is right: the bar is that a governed CLI is not weaker than the same
CLI on its own, and today it is. Filed as two, because they are not the same difficulty:

- **ENH-041 (P1) — the read-class half: `glob`, `grep`, `read_file(offset, limit)`.** Derived
  `reads` only, so no approval under `ask`, and that is most of your pain: today every search is a
  `run_shell` that stops a person on what is a read, and every large file arrives whole. Additive,
  low-risk, and it is the one to do first.
- **ENH-042 (P1) — the write-class half: an exact-string edit, a multi-file patch, a background
  shell with status and kill.** Harder, and the difficulty is the record, not the edit: an edit
  needs a typed refusal when `old` is absent or ambiguous, and a multi-file patch has to be atomic
  across files or the record lies about what happened.

**ENH-041 is done and in 0.35.0** — you named it first, so it went next, as a quick-task. What you
get:

- **`glob(pattern, path?, limit?)`** — `**` crosses separators, `*` does not; files only, sorted,
  paths relative to the workspace root while the pattern matches relative to `path`.
- **`grep(pattern, path?, glob?, limit?)`** — a regular expression over contents; each match is
  `{"path", "line", "text"}` with a 1-based line number; `glob` narrows the files; a file that
  cannot be read is skipped, not fatal; a bad pattern is refused naming it.
- **`read_file(path, offset?, limit?)`** — `offset` is the first line counting from 1, `limit` is
  how many. Without them it is byte-for-byte the whole-file string it always was, so nothing you
  have today changes.

Two behaviours to build on rather than guess at:

- **A cap is announced.** Under the limit you get a plain list; over it you get an object instead —
  `{"paths": …, "truncated": true, "found": N}` for `glob`, `{"matches": …, "truncated": true}` for
  `grep`. A model reads "there are more" rather than inferring "there are none". Defaults 1000 and
  200.
- **A range past the end is refused, naming the line count.** An empty string reads to a model as
  an empty file and it stops looking.

**And the reason it is the half worth having first:** `glob` derives from `list`, `grep` from
`read`, so their profiles carry no writes, no reach, no cost — **the shipped `ask` mode does not
stop a person for a search.** That was the actual cost of the gap: not that searching was
impossible, but that it went through `run_shell`, which `ask` rightly does stop.

### And the edit half went too — 0.36.0

You said whole-file rewrites "risk dropping content", and that was the part worth not waiting on.

- **`edit_file(path, edits[])`** — a list of `{old, new}` applied in order, **all of them or none**.
- **`move_file(from, to)`** — refuses a destination that already exists. Nothing moved a file
  before; `mv` through `run_shell` is a `run` effect, so it was irreversible *and* it asked.

**The refusals are the design, so build on them.** An `old` that is absent is refused because your
model's picture of the file is out of date — it should read again, not retry. An `old` that appears
more than once is refused naming the count, because taking the first is how an agent edits the
wrong line and reports success. Both refuse **before anything is written**, so a failed edit leaves
the file that was there. There is no `replace_all`: replacing every occurrence is a different act
and one a caller should have to say out loud.

**You do not need `previews_from` for edits.** `old` and `new` are the call's own inputs, so they
arrive on your approval card through `ApprovalRequested.inputs` *before* anyone approves, and on the
record through `Invoked.inputs` after. No disk read, no race with the agent. That was the thing we
got wrong in our own plan first — we were about to build a before/after capture that edits never
needed. (ENH-044 stays open for *whole-file* writes and deletes, where the inputs genuinely do not
say what was there.)

**What is still open in item 4:** a cross-file patch, and a background shell with status and kill.
Both stay unscheduled — this repository is maintenance and the successor is `shadow`. Tell us if
either is actually costing you, the way you told us about the edit.

---

## 5. Question — a resident CLI's lifetime, and where its sessions show.

- **`idle_seconds` is the switch, and it works in process.** `Thread.open`, `Thread.resume`,
  `Conversation.open` and `[provider] idle_seconds` — the same thing, served or embedded. After
  that long with no turn the provider session is closed and reopened on its id at the next turn.
- **The default is never.** So one process per open conversation is exactly what you have until you
  set a number, and you are right that it adds up. Set it on the order of a person's coffee break;
  the cost of being wrong is a session reopen, not a lost turn. A thread's own `close()` is still
  what ends the process group.
- **The sessions are in the person's history, and the kit does not move them.** The kit runs the
  vendor's binary *as the person* — that is what makes a subscription work at all — so its
  transcripts go where that binary puts them. We already strip `CLAUDECODE`, load no settings
  source, and turn auto-memory off (ENH-012), because a run's instructions should be the mode's
  behaviour; none of that relocates a transcript.
- **Is a separate config directory safe? Unmeasured, and treat it as suspect.** You can try it
  today with no kit change — `Provider.set_env`, or your own provider file. But `--bare` was
  measured and rejected for exactly this shape: it never reads the keychain, so it drops the
  subscription login along with the settings. Assume `CLAUDE_CONFIG_DIR` is the same hazard until
  somebody has watched a signed-in subscription survive it. If you measure it, send us the result
  and we will ship it as a default.

---

## Items 6–10 — the five the boundary moved to the kit

Taken in the spirit you sent them: for each, what exists, where, and whether it is on the roadmap.
The admission rule holds — none of these is a product concept.

### 6. Checkpoints and undo of an agent's changes — **not in the kit.** ENH-043 (P2).

The kit checkpoints the **run** (behind every park and resume) and the **record**
(`Thread.rollback(to_turn=)`, `fork()`). Neither touches the filesystem: a rollback rewinds what was
*said*, not what was *written*, so a thread rolled back to turn 3 faces a workspace still carrying
turn 7's files. That gap is real and we had not named it.

The design question is whether the kit ships one mechanism, a port with a git-backed adapter, or
only the record of what *would* be restored — cheap where a root is a work tree, expensive where it
is not. One constraint regardless: **a restore is itself a write**, so it is an act with effects
that the mode judges and the record carries. An undo that bypasses governance is a hole.

### 7. The diff of every change on the record — **not in the kit.** ENH-044 (P1), and the most
justified of the five.

Confirmed: `write_file` records `{"path": …, "bytes": N}`, `delete_file` records the path, and
`EffectRecorded` carries a digest and a free `detail` — no content anywhere. So
`told.previews_from(self._root())` is you reaching around the record to the disk, and it is not
just inelegant: it races the agent, and it cannot work at all for a contained or remote environment
where the host has no such access. Highest priority of the five for that reason. The open question
is the size cap and whether the *record* keeps the content or only the live event — a record that
keeps every file version is a different product, and we should decide that deliberately.

### 8. A live plan for a long task — **half of it exists, and not the half you need.** ENH-045 (P2).

What the *runtime* is about to do is already on the record: `Composed` is emitted every time the
composition changes ("so plan-versus-actual comes for free"), `PlanAdmitted`/`PlanRefused` carry a
whole plan's admission (D108/D116), and `items()` renders steps for a client. Read those first —
you may get more of your progress display from them than you expect.

What is missing is the agent's own narration — the field's to-do list, revised as it learns. A
governed CLI cannot say it today because its only tools are the registry's. The shape is a
registered component with no effects, so every mode admits it and the record carries the revisions
in order. Worth noting the boundary cuts here: the *mechanism* is ours, the plan's *content* is
yours.

### 9. Steering a turn midway — **it exists.** Use it.

`steer(text)` is there end to end and measured (D63): `Thread.steer`, `Conversation.steer`, the
wire's `turn/steer`, and `test_steer_reaches_a_provider_that_takes_it_mid_turn`. A resident CLI
reads its stdin during a turn, and a message written while the turn runs is queued and folded into
the same turn. It returns `bool`, and honestly: a one-shot dialect has no open stdin and says
`False`.

**The gap is key-backed models** — `ModelAgent.steer` returns `False` today, although the loop
between steps is ours and so is the one place it could be true. ENH-046 (P2).

### 10. A root's own instruction files — **deliberately off, and the other half is missing.**
ENH-047 (P2).

Your measurement was done under ENH-012 on 2026-09-12: with a sentinel `CLAUDE.md` in the
workspace the model quoted it, and with `--setting-sources ""` the sentinel was gone. So **no, a
governed Claude Code did not read them**, and that is deliberate — a run's instructions should be
the mode's behaviour, not a file someone left in a folder for a different tool. That default stays.

**One caveat on that measurement, and it is yours to weigh.** It was taken against claude
**2.1.235**; you are on **2.1.284**. `--setting-sources ""` is the CLI's own documented switch and
we have no reason to think it moved, but that is a long gap to assume across — and BUG-031 is the
precedent, where a later CLI shipped a new built-in (`Monitor`) that the deny list written for an
earlier one did not name. If you want it re-measured against the version you actually ship, say so
and we will run the sentinel test on 2.1.284 rather than infer it.

But you have found the real gap: **the kit never offers them either.** A team convention written
where the field writes it reaches no provider, and a key-backed model never had them at all. The
shape is the workspace reading a root's instruction file and folding it into the turn's context as
data the mode's behaviour frames — named, attributable, refusable, not an unmarked prefix — and
identically for a CLI and a key-backed model. This is the context-engineering phase the roadmap
already names (Phase 55, canonical in `shadow`).

---

## What you need to do

1. **Pin `shadow-hdk==0.36.0`** for 0.6.11. Additions only; the *Pins* row is the minor bump, and
   nothing you call today changes shape.
2. **Check `approvals=` is passed** before rearchitecting anything for item 3 — read §3 above. It
   matches the symptom you described exactly, and it is a one-line check.
3. **Set `idle_seconds`** if one process per conversation is costing you. The default is never.
4. **Point your guidance at the new operations**: `glob`/`grep` rather than `run_shell` for
   search, `read_file(offset, limit)` for anything large, `edit_file` rather than `write_file` for
   a change, and `move_file` rather than `mv`. That is where both the `ask`-mode interruptions and
   the dropped-content risk go away.
5. **Say whether the cross-file patch or the background shell is costing you**, the way you told
   us about the edit — that is what decides whether either is carried here or left to `shadow`.
6. If you measure `CLAUDE_CONFIG_DIR` against a signed-in subscription, send the result and we will
   ship it as a default.

**On the gate, honestly.** CI is green for all three releases — macOS, Landlock, bubblewrap and
Python 3.12/3.13/3.14 — and each was verified after publishing by installing from PyPI into a
clean environment and exercising the new operations there, not only in the test suite.

You should know the shape of that evidence rather than just the word "green". While we were
building this, **five distinct tests failed on code that could not have caused any of them** — on
a laptop under load and on CI runners alike, each green on a re-run of the same commit. Two of our
own releases therefore went out with a gate we had to reason about rather than simply read. We
have since fixed the cause rather than living with it (TD-015): tests now wait for the condition
they need instead of for a fixed number of seconds, and the wall-clock latency budget runs where
the measurement is worth trusting instead of in every local run.

One more, in the same spirit, because it touches something you depend on: the Linux helper's
wheels were **not reproducible** — the same commit built twice gave different bytes, which we only
discovered by re-running a publish. That wheel is the confinement mechanism, and a binary nobody
can rebuild and compare is a binary taken on trust. It is fixed and CI now proves it on every run
(TD-016). The practical consequence for you is small but worth knowing: **0.36.0's helper wheel is
the last one that cannot be reproduced**; every release after it can.

Records, if you want the detail: `specs/adhoc/BUG-226-228/record.md`, `specs/adhoc/ENH-041/record.md`,
`specs/adhoc/ENH-042-a-change-names-a-region/record.md`, `specs/adhoc/TD-015-TD-016/record.md`.
