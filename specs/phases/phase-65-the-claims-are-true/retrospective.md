---
type: Retrospective
phase: phase-65-the-claims-are-true
---

# Phase 65 retrospective — the claims are true

## What this phase was

Lane P's audit of 2026-10-02 lists forty items. Eight of them are not requests for capability — they
are claims this kit already makes that are not true. The owner's decision was **Wave 1 only**: build
the A-group, nothing else, on the ground that new capability belongs to the native line rather than to
a maintenance-supported implementation. Every other audit item is named in the overview's *Out* so no
later reader mistakes it for an oversight.

Five of the eight were confirmed against the source before the phase opened — the audit asked for
exactly that, and it was right to. **Three of the five originate in my own phases 62 and 64.**

| | what was claimed | what shipped |
|---|---|---|
| BUG-230 | `tools_offered` narrows what a model is shown | nothing narrowed, and two fields reported it honoured |
| BUG-231 | a mode's `model` reaches a key-backed model | the only real `ModelPort` discarded it |
| BUG-232 | — | a key-backed thread forgot its turns and nothing said so |
| BUG-233 | — | 600s of total turn time, counting a person's thinking |
| BUG-234 | an agent is selectable per mode and readable on the thread | true only for a thread never switched and never resumed |

## What went well

**Confirming before fixing was worth the hour.** Every one of the five was real, and reading the
source first changed two of the fixes. BUG-230 would have been closed in the in-process catalogue
alone — leaving the claim false for Claude Code and Codex, which are handed no catalogue and *ask* the
registry. BUG-231 needed no kernel change at all, because `ModelRequest.model` was already there.

**The mutation pass found three things no test did**, and each was a defect rather than a weak
assertion:

1. The `| {"tools_offered"}` union in `unmapped_behaviour` was **dead code** — the function walks five
   field names and that is not one of them — so the lie was *inert*, and the test I wrote to cover it
   passed vacuously.
2. `_compact` kept `messages[:2]` as *the role and the brief*. With a transcript between them that is
   the role and the **oldest carried message**, so the request being answered would have been
   summarised away. I introduced that risk in the same group and the mutation caught it in the same
   hour.
3. A *resumed* thread had no agent override, so the same `set_mode` behaved differently before and
   after a restart. Found because a mutation on an unreachable default value survived.

**And a fourth, found by re-reading rather than by a test.** Lane P asked which version fixes their
BUG-258 (*Claude Code gets no tools in the installed desktop app*). Reading G1 against the code path
that defect lives in showed that the narrowing reached a CLI's **calls** and not its **listing**
(BUG-235): a narrowed Claude Code was served the whole catalogue and then refused *no component
named …* for anything it picked. My G1 tests asserted on the refusal and never on the length of the
served list — the narrowing was tested through the door that refuses and not the door that offers. A
narrowing has two doors, and a test has to walk both.

**Three equivalent mutants were resolved by deleting code, not by inventing tests.** Redundant guards
that no test could distinguish were removed. A branch no test can tell from its absence is a branch
claiming to matter when it does not.

**The invariants earned their keep twice.** `test_the_runtime_imports_no_adapter` caught `agent_now`
imported into `runtime/conversation.py` — the pure decisions moved to `kernel/threads.py` and the
adapter re-exports them. The wire-parity invariant caught `Thread.agent` becoming public surface that
neither crossed nor said why.

**Changing what is measured beat changing a number.** BUG-233's obvious fix is a bigger timeout. The
right fix is that a ceiling is a hang detector, so it measures the gap between frames; the default
moved too, precisely because the number now means something else and leaving 600 would have invited
the next reader to assume nothing had changed.

## What was harder than it should have been

**TD-019 shaped the whole phase.** A failing test that stands up a `ServeHost` hangs rather than
failing, so no mutation pass can use one. G5's decisions were extracted into pure kernel functions and
a host-free thread harness was built for the wiring, with the `ServeHost` tests kept as behavioural
coverage. That is a good shape on its own, but it was forced, and it cost real time twice — once when
a diagnostic run hung and had to be killed. The debt is still open.

**I broke ninety-two runtime tests in one edit** by making `Thread.agent` a property while
`ServeHost` still assigned to it, and compounded it by adding a keyword to `Conversation.open` in one
step and the parameter in another — a cell that raised before writing, so an edit I believed had
landed had not. Reading the failure rather than guessing took one command; believing a `print` instead
of checking the file cost three.

**Two of my own tests were nearly vacuous.** The override-survives-a-switch test switched into a mode
naming the same agent as the override, so the mode's own answer happened to be right. The
narrowing-honesty test asserted an empty list against a function that could never have returned
anything else. Both passed. Only mutation showed them for what they were.

## What to carry forward

- **Confirm a reported claim against the source before fixing it.** Two of five fixes changed shape
  because of what reading found.
- **A pure function per decision, where a host would otherwise be needed.** Not a workaround for
  TD-019 any more — it is simply where a decision belongs if it is to be checkable.
- **Pair every honesty assertion against something that must still be reported.** An assertion that
  something is *absent* passes against a function that reports nothing at all.
- **Make the two sides of a false claim move in one change.** The behaviour and the field that
  describes it were corrected together, because the two disagreeing was the defect.
- **A mechanism with two doors needs a test at each.** BUG-235 passed every G1 test because they all
  went in through the refusal. The question to ask of any gate is *what does the other side see*.
- **A skip must say what it needs.** TD-020's live legs now name the account required and what the
  measurement would prove. A silent skip is how an unmeasured claim stays unmeasured.

## Debts filed

| | |
|---|---|
| ENH-052 | the carried transcript is unbounded; a token ceiling and a compaction that fires on it are the audit's H33/H34, outside Wave 1. Filed at the moment the risk was introduced, and named in the comment that introduces it |
| TD-020 | Codex's instruction fold has never run end to end — this laptop's Codex refuses every model offered it. Needs an account where it accepts one; the skip now says so |
| TD-019 | still open, and it shaped this phase |
| BUG-235 | filed **and closed** in this phase: my own G1 defect, above |

## Verification Evidence

Captured 2026-10-02 on `phase-65-the-claims-are-true`, macOS 26 (Darwin 27.0.0), Python 3.14.6.
`pytest`'s output read from a file rather than through a pipe, and its exit code read directly — a
`tail` in the pipeline once reported `exit=0` over two failures, and that lesson is now in every one
of these.

This retrospective is written **before** the final gate is run against the tree that carries it. The
v0.41.0 tag went red on every CI job because a retrospective quoted a document absent from its own
tree; a document is part of the tree the gate checks.

### `uv run ruff check .`

```
All checks passed!
```

### `uv run ruff format --check .`

```
538 files already formatted
```

### `uv run mypy`

```
Success: no issues found in 507 source files
```

### `uv run pytest`

```
2144 passed, 20 skipped, 23 deselected, 85 warnings
exit=0
```

The wall-clock figure is left out on purpose: it differs between runs, so quoting one makes the
retrospective disagree with the next gate over something that was never the claim. The counts and the
exit code are what the gate asserts.

Suite 2058 → 2144 across the phase. Fifty-four mutations verified: eleven in G1 (two of them on
BUG-235's fix), seven in G2, nine in G3, ten in G4, twelve in G5, with five survivors — three equivalent mutants resolved by deleting the
code, and two genuine test weaknesses that became the findings above.

### Live, opted into with `-m live`

```
tests/test_instructions_reach_a_live_model.py ..ss
2 passed, 2 skipped in 17.38s
```

The two Claude Code legs ran against a real model with `--system-prompt` removed from its record, so
the fold is the only way in, and the paired negative shows the sentinel is not something it says
anyway. The two Codex legs skip, saying what account they need and what they would prove (TD-020).
