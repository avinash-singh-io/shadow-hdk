---
type: Evidence
phase: phase-66-the-short-list
group: G2
---

# H11 — the gaps, confirmed against the source

**Read 2026-10-03 at `f693827` (v0.44.0).** Reported before anything is built, because three of phase
65's five items needed a different fix than the audit assumed and two were already partly done.

H11 asks for *one agent definition every provider honours*, a row carrying **instructions, tools,
skills, model, effort, mode, fragments, a description and sub-agent limits**, where a CLI gets
everything but its own loop and a key-backed model gets all of it.

## Summary

The audit's *"agents are honoured on key-backed hosts only"* is right, and **the reason is worse than
it reads**: on a CLI host a named agent is not merely unhonoured, it is unvalidated and unreported.
But the two mechanisms a CLI would need already exist and are measured, so H11's CLI half is
**wiring, not new capability** — a much smaller job than the audit implies.

| | finding | severity | size |
|---|---|---|---|
| A | on a CLI provider a named agent is silently dropped, **and an unknown name is not refused** | **P1 — a defect** | small |
| B | what a CLI could honour needs no new mechanism: both halves shipped in 0.38–0.44 | — | small |
| C | three `Pattern` fields a stored row cannot set, `plan` among them — which *is* H11's "sub-agent limits" | P2 | trivial |
| D | a row has no `description`; `agents/list` derives the line from the role prompt | P3 | trivial |
| E | skills cannot be bound to an agent **as data**, though the runtime supports it | P2 | small |
| F | `model`, `effort`, `fragments`, `mode` are on the **mode** by design, not the agent | not a defect | a decision |

## A. The defect: a CLI drops a named agent without validating or reporting it

`ServeHost._agent_named` (`serve/host.py`) returns `None` whenever the host has no model — which is
every CLI host:

```python
if self._handed_agent is not None or self._model is None:
    return None
pattern = await self.patterns.named(wanted) if wanted else single
```

Three consequences, in order of how much they matter:

1. **The D176 refusal never runs.** `patterns.named(wanted)` — which raises `NoSuchAgent` naming what
   exists — is on the line *after* the early return. So on Claude Code or Codex a mode naming
   `"reviewr"` is accepted in silence. D176 says an unknown agent name is refused at open, naming it;
   that is true on a key-backed host and false on a CLI. **A claim the kit makes and does not keep**,
   the same category as all of phase 65.
2. **Nothing says the agent was dropped.** `agent_recorded(wanted, chosen=False)` records `""`, which
   the contract defines as *no agent applies*. That is honest about the kit's choice but says nothing
   about the product's request. There is no `unmapped_behaviour` equivalent for agents, so a product
   that set an agent and got the CLI's own loop has no field to read.
3. **So the capability silently depends on the provider**, which is exactly the shape of ENH-051
   (instructions never reached Codex) and BUG-229 (a key-backed model never received them *and* the
   thread said it had).

**Recommendation:** fix (1) and (2) regardless of what else is decided. Validate the name on every
path — the refusal is cheap and a typo should never be silent — and name a dropped agent so a product
can read it. This is the H11 item worth doing first.

## B. What a CLI could honour — both mechanisms already exist

The audit's own shape for this is *"instructions by flag or fold, tools through the relay, its own
skills only."* Both are built:

| the agent row carries | the mechanism that would deliver it | shipped |
|---|---|---|
| `system` | the behaviour-flag path (D64) and, for a CLI mapping no flag, `instructions_in_prompt`'s fold — **measured live** on Claude Code with its flag removed | 0.38.0, 0.41.0 |
| `tool_names` | `Offer.narrow_to` / `shows()`, which narrows both the list a CLI is served and what it may call | **0.44.0** |

So the work is to resolve the agent on the CLI path and feed its `system` into the instruction channel
and its `tool_names` into the narrowing. No new port, no new contract.

**One decision this forces.** A mode's `Behaviour.tools_offered` and an agent's `tool_names` are both
allow-lists over the same registry. They must **intersect**, not override: narrowing is applied last
precisely so it can only take away (D178), and two allow-lists where the later widens the earlier
would break that. Recommended: intersect, with the same refusal for a name nothing answers to.

## C. Three `Pattern` fields a stored row cannot set

`Pattern` has eleven fields. `loader.KEYS` accepts eight. Not settable from a stored row:

- **`plan`** (`PlanLimits`) — this is H11's "sub-agent limits". The field exists, the row cannot reach it.
- `absorb`
- `offload_over`

**Recommendation:** add `plan` to `KEYS` with parsing, since H11 names it. `absorb` and
`offload_over` are loop-tuning knobs nobody has asked for; add them only if asked, and say so rather
than adding by symmetry.

## D. No `description`

`agents/list` returns a `description`, and it is derived from `system` — the test pins
`reviewer["description"].startswith("REVIEWER-ROLE")`. So a product showing a person an agent chooser
shows them the opening of a role prompt, which is written for a model, not for a person.

**Recommendation:** one optional `description` field, falling back to today's behaviour when absent.
Trivial, and it is the difference between a usable chooser and a leaky one.

## E. Skills cannot be bound to an agent as data

`ModelAgent(..., skill=...)` exists and `AgentSession` reads `self.agent.skill`, checking its declared
needs before the first turn (D17, BUG-012). So the **runtime** supports an agent bound to a skill. But
`Pattern` has no skill field and `pattern_from` accepts no such key, so **a stored row cannot name
one** — only a host composing in Python can.

**Recommendation:** an optional `skill` name on the row, resolved against the skill registry at open
with the same refusal-by-name as an agent. Small, and it is the half of H11 that makes a plugin's four
agents actually different from each other.

## F. `model`, `effort`, `fragments`, `mode` — on the mode by design

These are not missing; they are **somewhere else on purpose**. D64 puts `Behaviour` on the mode —
`system`, `append_system`, `model`, `effort`, `temperature`, `tools_offered`, and since 0.44.0
`silence_seconds`. D175 then has the **mode name the agent**, so that switching agent goes through
`set_mode`, a door that is already governed and already recorded.

H11 asks for the inverse: an agent row carrying its own model and effort.

**Recommendation: do not move them, and let the owner overrule me if the product needs it.** Reasons:

- It would create **two sources of truth** for the same field, and the kit would have to resolve
  agent-versus-mode conflicts on every open. There is no obviously right answer to that, which is a
  sign the field belongs to one of them.
- A product that wants *this agent always runs on that model* can already write a mode per agent.
  That is one row, not a mechanism.
- D175's reason for putting the selector on the mode was that a mode is governed and recorded. An
  agent row carrying a model would let a stored row change which model a run costs money on, without
  passing the door a product's governance watches.

If the owner wants it anyway, the honest shape is **the mode wins where both name one**, with the
agent's value as a default — and `unmapped_behaviour` naming the agent's value as not honoured when
the mode overrode it.

## Proposed order for G5, if approved

1. **A** — validate on every path, and report a dropped agent (the defect).
2. **B** — the agent's `system` and `tool_names` honoured on a CLI, intersecting with the mode's.
3. **E** — `skill` on the row.
4. **C** — `plan` on the row.
5. **D** — `description` on the row.
6. **F** — not built, pending the owner.
