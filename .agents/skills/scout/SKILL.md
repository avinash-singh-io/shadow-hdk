---
name: scout
description: "Read-only context fetch from one ecosystem member repo. Returns a structured summary, writes a scout-NNN.md run artifact, and appends one line to the ecosystem session log. Activates when the user invokes /scout or asks momentum to run the scout recipe."
---

Read-only context fetch from one ecosystem member repo. Returns a structured summary, writes a scout-NNN.md run artifact, and appends one line to the ecosystem session log.

> **Three doors, one library.** This is the slash-command door for Codex. The CLI door is `momentum scout <repo> "<prompt>"` and the natural-language inference door fires when the user describes a single-repo, read-only context-fetch task without naming a primitive. All three doors call `core/orchestration/scout.js` so the output shape is identical.

## When to use

- You're about to make a change in this repo but you need to know the current state of a related repo first (auth shape, API contract, schema, recent decisions).
- A user asks "what's the situation in `<repo>`?" — that's scout.
- You want a durable record of a context-fetch you just did, not just a chat message.

## Inference guidance (read this in non-slash contexts too)

Treat ANY of these as a scout invocation even without an explicit `/scout`:

- "What's the current X in repo Y?"
- "Before I make the change here, get me the latest state from `<sibling repo>`."
- "Read repo Y and tell me about its current Z."

When inferring, narrate it: `▸ inferred: scout (single repo, read-only). Use /scout next time for predictable behavior.`

Do NOT use scout for multi-repo questions — use `/dispatch`. Do NOT use scout when you're about to write into the target repo — use `/handoff`.

## Usage

```
/scout <repo> "<prompt>"
```

`<repo>` is either a member id from `ecosystem.json` or a relative/absolute path. `<prompt>` is the user's question.

## Steps

### Step 1 — Identify the target repo + prompt

Parse the user's invocation and resolve `<repo>` to an absolute path via the ecosystem manifest (`ecosystem.json` → `members[]`).

### Step 2 — Read the target repo in-process

Codex's `parallelSubagents` is currently declared `false` in `core/adapter-capabilities.md` (pending live validation). For a single-repo read-only task this is irrelevant — scout is naturally a single sub-agent. Use Codex's sub-agent surface to:

1. Read `specs/status.md` and recent files under `specs/architecture/` and `specs/phases/<active>/history.md`.
2. Read any keyword-matching files.
3. NO writes. Read-only is the contract.
4. Return a structured result with `summary`, `filesRead`, `findings` (each finding meeting Rule 3 criteria for `[DISCOVERY]` tracking).

### Step 3 — Record the run

Once the sub-agent returns, call into the orchestration library:

```js
const orchestration = require('<momentum-root>/core/orchestration');
const result = orchestration.scout.record({
  repo: '<resolved repo path>',
  prompt: '<user prompt>',
  summary: '<sub-agent summary>',
  filesRead: [/* ... */],
  findings: [/* ... */],
  ecosystem: { rootPath: '<ecosystem root>', memberId: '<this repo member id>' },
  duration: <ms>,
});
```

This writes `.momentum/runs/scout-NNN.md` in THIS repo (originating) and appends one line to the ecosystem session log.

### Step 4 — Hand findings to the tracking contract

```js
orchestration.tracking.proposeDiscovery({
  primitive: 'scout',
  finding,
  targetRepo: '<scouted repo path>',
});
```

The helper applies Rule 3 criteria; only meaningful findings land in the scouted repo's active phase `history.md` as `[DISCOVERY]`. NEVER use a `[SCOUT]` marker.

### Step 5 — Narrate the result

Print the summary, the artifact path, and the session log reference.

## Tracking contract

- **Auto every time:** ecosystem session log line + scout-NNN.md artifact in THIS repo.
- **Auto only when meaningful:** `[DISCOVERY]` in scouted repo's active phase history.
- **Never:** `backlog.md` entries without explicit user confirmation.

## Errors

- Repo not found in ecosystem manifest → report and stop.
- Repo not in any ecosystem → fall back to running scout in-process via CLI; suggest `momentum scout <path> "<prompt>"`.
