---
name: momentum-orient
description: Read specs/status.md before starting any work in a momentum-managed project. Activates at the start of every new task to ensure the agent has current phase context. Codifies Rule 1 (Orient First).
---

# momentum-orient

When this skill activates (at session start or when the user asks you to
work on something new), read these files in order before any other action:

1. `specs/status.md` — current phase, blockers, P0 items, next actions
2. `specs/backlog/backlog.md` — P0/P1 items that may block the current task
3. `specs/phases/<active-phase>/tasks.md` — what's done / in flight / blocked
4. `AGENTS.md` — project rules and constraints (the complete rulebook)

Then proceed with the user's request, framing any output in terms of:
- which phase is active
- whether the requested work belongs in the active phase or is a side track
- any existing tasks or history entries that already cover the request

This skill is shipped by the momentum toolkit. It codifies Rule 1 (Orient
First) from the project rules. See `AGENTS.md` for the full set of rules.

## When NOT to apply this skill

- If the user's message is purely conversational ("what is X?") and doesn't
  require touching the codebase, you don't need to orient.
- If you've already oriented this session and nothing on disk has changed
  since, don't re-orient.
