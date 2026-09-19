---
name: dispatch
description: "Parallel multi-repo fan-out + synthesis. One sub-agent per listed repo with auto-tailored prompts; all results synthesised into a single answer to the user's high-level intent. Writes one dispatch-NNN.md artifact and one session log line. Activates when the user invokes /dispatch or asks momentum to run the dispatch recipe."
---

Parallel multi-repo fan-out + synthesis. One sub-agent per listed repo with auto-tailored prompts; all results synthesised into a single answer to the user's high-level intent. Writes one dispatch-NNN.md artifact and one session log line.

> **Three doors, one library.** This is the slash-command door for Codex. The CLI door is `momentum dispatch <r1> <r2> ... --prompt "<text>"` and the natural-language inference door fires when the user describes a multi-repo audit / alignment task. All three doors call `core/orchestration/dispatch.js` so the output shape is identical.

## When to use

- "What breaks if I rename X across all repos?" — multi-repo audit.
- "Get me the current state of A AND B so I can align a change." — pre-coordination context fetch.
- "Where does Y come from across the stack?" — cross-cutting investigation.

## Inference guidance

Treat ANY of these as a dispatch invocation:

- "Audit X across repos A, B, C."
- "What's the state of A, B, and C right now?"
- "Find every place that does X across the ecosystem."

When inferring, narrate `▸ inferred: dispatch (multi-repo audit). Use /dispatch next time for predictable behavior.`

## Usage

```
/dispatch <repo1> <repo2> [repo3 ...] "<user intent>"
```

## Capability-routing note

Codex declares `parallelSubagents: false` in `core/adapter-capabilities.md` pending live validation of parallel subagent fan-out. The capability-routing helper will return `mode='sequential'` for Codex; surface the note up front:

```
▸ note: this adapter does not declare parallel subagents — running sequentially (Promote to true once dispatch parallel mode is exercised against Codex in CI.)
```

In sequential mode, run sub-agents ONE AT A TIME via Codex's subagent surface. Output shape stays identical to parallel mode — just slower.

## Steps

### Step 1 — Identify the targets + intent

Resolve each repo arg via `ecosystem.json`.

### Step 2 — Capability-route the dispatch mode

```js
const orchestration = require('<momentum-root>/core/orchestration');
const adapter = orchestration.capabilityRouting.loadAdapter('<momentum-root>', 'codex');
const { mode, notes } = orchestration.capabilityRouting.chooseMode(adapter, 'dispatch');
```

Surface each note via `▸ note: <text>` BEFORE starting sub-agents.

### Step 3 — Fan out (sequential on Codex today)

For EACH target repo, invoke a Codex sub-agent with:

- System prompt: "You are a DISPATCH SUB-AGENT for momentum's quick-verb layer. The user intent is authoritative — if it asks to audit / investigate / report, stay read-only. If it asks to fix / refactor / migrate, you may write code, but commit on a feature branch per Rule 6 and surface the branch name. Return a JSON result with summary, filesRead, optional filesWritten + branch, findings (Rule-3 thresholds)."
- Task prompt: user intent + the specific repo.

Capture failures in `failures[]`; never abort the whole dispatch.

### Step 4 — Synthesise

Read all per-repo results IN THIS AGENT'S CONTEXT and produce a synthesis paragraph that DIRECTLY ANSWERS the user's intent.

### Step 5 — Record the run + tracking-contract hand-off

```js
orchestration.dispatch.record({
  repos, userIntent, mode, modeNotes: notes,
  perRepoResults, failures, synthesis,
  originatingRepo, ecosystem, duration,
});
```

Then for each finding:

```js
orchestration.tracking.proposeDiscovery({ primitive: 'dispatch', finding, targetRepo });
```

Synthesis-level note:

```js
orchestration.tracking.proposeHistoryNote({
  primitive: 'dispatch',
  originatingRepo,
  message: '<one-line summary>',
  runArtifactRef: '<.momentum/runs/dispatch-NNN.md>',
});
```

### Step 6 — Render

```
▸ Synthesis
<paragraph>

▸ Per-repo
  ▼ <repo1>: <one-line>
  ▼ <repo2>: <one-line>

→ logged to sessions/<today>.md
→ trace at .momentum/runs/dispatch-NNN.md
```

## Tracking contract

- Auto: session log line + dispatch-NNN.md.
- Auto if meaningful: per-repo `[DISCOVERY]` + originating `[NOTE]`.
- Never: `[DISPATCH]` entry types; `backlog.md` without confirmation.
