---
name: continue
description: "Pick up a pending handoff in this repo. Reads `.momentum/inbox/handoff-NNN.md`, parses the structured context block, marks the inbox file as read, and emits a `[NOTE]` in the receiving repo's active phase history. Activates when the user invokes /continue or asks momentum to run the continue recipe."
---

Pick up a pending handoff in this repo. Reads `.momentum/inbox/handoff-NNN.md`, parses the structured context block, marks the inbox file as read, and emits a `[NOTE]` in the receiving repo's active phase history.

> **Three doors, one library.** This is the slash-command door for Codex. CLI: `momentum continue [--handoff <id>]`. SessionStart hook auto-greets pending handoffs. All three call `core/orchestration/continue.js`.

## Usage

```
/continue                     pick up the OLDEST pending handoff
/continue <id>                pick up handoff-<id> specifically
/continue list                list pending handoffs without picking
```

## Steps

### Step 1 — List or pick

```js
const orchestration = require('<momentum-root>/core/orchestration');
const block = await orchestration.continueHandoff.continueHandoff({
  repo, handoffId, ecosystem,
});
```

### Step 2 — Act on the block

Narrate summary, decisions, files, verification commands, open questions. Proceed with the work.

### Step 3 — Don't surprise the user

Large blocks → summarise + offer "want me to read the full block?".

## Tracking contract

- Auto: inbox file → `read/` + `[NOTE]` in receiving active phase history.

## Errors

- No pending → "no pending handoffs in this repo" (not an error).
- Specified id not found → error with list of pending ids.
- Malformed inbox → error pointing at the file.
