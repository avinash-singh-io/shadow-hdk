---
name: handoff
description: "Cross-session control transfer with a structured context block. Writes `<toRepo>/.momentum/inbox/handoff-NNN.md` so a fresh agent session in that repo can pick up where you left off, and emits a `[DECISION]` in this repo's active phase history. Activates when the user invokes /handoff or asks momentum to run the handoff recipe."
---

Cross-session control transfer with a structured context block. Writes `<toRepo>/.momentum/inbox/handoff-NNN.md` so a fresh agent session in that repo can pick up where you left off, and emits a `[DECISION]` in this repo's active phase history.

> **Three doors, one library.** This is the slash-command door for Codex. The CLI door is `momentum handoff <repo>`; natural-language inference fires when the user describes a control transfer. All three doors call `core/orchestration/handoff.js`.

## When to use

- You finished work in repo A and want the next Codex session in repo B to continue with full context.
- You hit a stopping point that requires switching repos and want decisions preserved.

## Usage

```
/handoff <repo> [optional one-line summary]
```

## Steps

### Step 1 — Identify the target

Resolve `<repo>` via `ecosystem.json`.

### Step 2 — Collect the context block

Pull from this session:
- decisions made
- files touched
- verification commands the receiving agent should run
- open questions

### Step 3 — Write the handoff

```js
const orchestration = require('<momentum-root>/core/orchestration');
const block = await orchestration.handoff.handoff({
  fromRepo, toRepo, summary,
  decisions, filesTouched, verificationCommands, openQuestions,
  ecosystem,
});
```

This writes `<toRepo>/.momentum/inbox/handoff-NNN.md`, appends one line to the ecosystem session log, AND emits a `[DECISION]` in this repo's active phase `history.md`.

### Step 4 — Tell the user

```
▸ handoff written: <toRepo>/.momentum/inbox/handoff-NNN.md
▸ logged [DECISION] in <originating phase>/history.md

Next: open a fresh Codex session in <toRepo>. The SessionStart hook
will detect the handoff and prompt. Or run `/continue` (or
`momentum continue`) explicitly.
```

## Tracking contract

- Auto: session log + inbox file + originating `[DECISION]`.
- Never: `[HANDOFF]` entry type. Use `[DECISION]`.
