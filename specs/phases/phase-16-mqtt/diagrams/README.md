---
type: Guide
phase: 16-mqtt
---

# Phase 16 — five views of the MQTT adapter

One diagram answers one question. These five answer five, and together they say what
[`../design.md`](../design.md) says in prose. Each `.json` is the source; each `.html` is a
self-contained page with themes, pan and zoom, search, tracing, and curated views.

| Question | Kind | Open |
|---|---|---|
| Who talks to whom, and where is the package boundary? | architecture | `mqtt-adapter.architecture.html` |
| What happens, in order, when the agent commands a valve? | sequence | `mqtt-act.sequence.html` |
| Which states can the link be in, and which of them reopen? | lifecycle | `mqtt-link.lifecycle.html` |
| Where does each payload land, and what does it become? | dataflow | `mqtt-messages.dataflow.html` |
| What are all the outcomes a step can observe? | workflow | `mqtt-act-outcomes.workflow.html` |

Each page carries curated views in its header — the architecture has *the act*, *a reading* and
*the package boundary*; the sequence has *lazy connect*, *two words for done* and *the record*.

## Why five and not one

- The **architecture** shows structure and layering. It cannot show order, so it cannot tell you
  that the ack subscription precedes the publish.
- The **sequence** shows order and the two distinct words for *done*. It cannot show the states
  between acts, so it cannot tell you that a broken link reopens while a closed one does not.
- The **lifecycle** shows those states. It says nothing about payloads.
- The **dataflow** shows where each payload lands: latest per sensor filter, a deque per witness
  filter, a waiter per key. It does not enumerate failures.
- The **workflow** enumerates them: every observation an actuator step can produce, and what each
  one leaves behind in the world.

## Regenerating

The skill lives at `~/.claude/skills/archify`. From that directory:

```bash
node bin/archify.mjs deliver architecture <spec>.json <out>.html --quality showcase --json
```

Every page here passed that showcase gate with zero composition errors and zero warnings.
Automated browser evidence is **skipped** on this machine: `visual-check` needs Chrome or
Chromium, which is not installed. The `*.visual-check.json` receipts record that.
