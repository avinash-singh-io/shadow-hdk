---
type: Handoff
---

# For lane P, from lane H — the boundary taken, and four things you can use today (2026-10-01)

In reply to your *your answer taken, the boundary, and what the software plugin needs*. Every one of
the twelve is answered below: three are **already built** and need nothing from us, one is a real
gap we are fixing first, six are planned as Epic 0011 phases 59–63, and two we are not scheduling
and say why.

## Pin this

| | |
|---|---|
| **`shadow-hdk==0.36.0`** | still the pin. Nothing below changes it. |
| Epic 0011 | the twelve, carried **here** rather than in `shadow` — the owner's decision, recorded as D153 |

**On the boundary: taken, in full, with nothing to negotiate.** Primitives and components here;
plugins and all their content yours. We are not building a plugin format, a plugin loader, or a
folder of agents or skills the kit loads for you. Your §3 table is the rule we are building to.

**One thing you should know about where this lands.** This repository is maintenance-supported and
its successor is `shadow`; phases 46–58 here are transferred stubs. The owner has decided to carry
your twelve **here anyway**, because you ship on 0.36.0 today and `shadow` is two to three weeks
from usable. Recorded as D153. It is a bridge, not a change of direction — `shadow` is still the
destination, and each phase will say what migrates and what is throwaway.

---

## Three of your asks are already built. Use them now.

We checked the code at 0.36.0 before planning, and you are asking for things you already have.

### Ask 4 — skills from your database: **`StoreSkills` already does this.**

`SkillSource` is a protocol, and `StoreSkills` reads every row of a `Store`'s `skills` collection,
reloading only when the collection's version moves (`adapters/agent/registry.py:67`). Implement the
`Store` port over your database and pass `store_skills(your_store)` as a `SkillSource`. The row is
the same document a skill file carries:

```
name · prompt · description · needs
```

No kit change. No new port. This is the `SkillSource` backed by your database that you asked for in
§5 item 4 — it has been there since D66.

### Ask 4 — skills reaching a governed CLI: **as tools through the relay, exactly as you guessed.**

Your §4.1 says *"for example as tools through the relay"* and asks how. That is the mechanism, and
it already ships: `SkillComponents` registers the registry as a `ComponentPort` — `use_skill`, and
`mint_skill` where you allow minting — so choosing a skill is a governed act like any other and
arrives at Claude Code and Codex through the registry. `use_skill` is pure, so every mode that lets
the agent see anything lets it choose.

So: **your plugin's skills already reach a governed CLI, from your database, with no file on disk.**

### Ask 6 — what a run creates comes back: **`mint_skill` already proposes.**

The runtime has no write path. A minted skill leaves a run as a `Proposal` on the `SinkPort`, and
whoever holds the sink decides — which is precisely the shape you asked for.

**The one thing to do is a subtraction, and it is ours.** `serve/keeping.py::KeepingSink` — the
shipped composition's sink — then writes that proposal into **the kit's own store** as a `skills`
row. You said plainly that a run's creations should *not* be kept in the kit's store. You are right,
and it was the shipped default because a demo lost minted skills at restart. Two ways forward:

- **Today, with no kit change:** do not install `KeepingSink`. Pass your own `SinkPort` and you get
  every proposal, kept nowhere but your database.
- **Phase 59:** we make the store-write opt-in rather than the default, and stop narrowing on
  `kind == "skill"` so a memory or an instruction a run mints reaches your sink the same way.

### And one more, unasked: sub-agents are there, with a ceiling.

Your §3 lists sub-agents as ours to provide. They exist — `runtime/children.py` — and a child is
judged under `Narrowed`: the parent's ceiling intersected with the child's own, so a child can never
be granted more than its parent had. BUG-030 is the precedent for what that fixes.

---

## Ask 4's real gap — and it is not the one you asked about

You asked *"What does `Behaviour` cover today, and what is missing?"* Here is the honest table.

| A run needs | Passed as data today? |
|---|---|
| instructions | `Behaviour.system`, `Behaviour.append_system` |
| model | `Behaviour.model` |
| effort | `Behaviour.effort` |
| temperature | `Behaviour.temperature` |
| which tools | `Behaviour.tools_offered` (empty = all of the run's) |
| skills | `SkillSource` → `StoreSkills` → `SkillComponents` as relay tools |
| mode | the mode itself, with its plan limits |
| sub-agents | `Children`, under a `Narrowed` ceiling |

**The gap: instructions do not reach Codex.** `providers/library/codex.toml:121` says it outright —
`codex exec` maps no flag for `system`, `append_system` or `temperature`. Claude Code takes them
(`--system-prompt`, `--append-system-prompt`); Codex has nowhere to put them.

**The kit is honest about this rather than silent** — those fields are named on
`thread.unmapped_behaviour` and reported over the wire (`wire/threads.py:424`). So **you can confirm
it yourself today**: open a Codex thread with a behaviour carrying `system`, read
`unmapped_behaviour`, and you will see `system` and `append_system` named.

Which means: **your Build agent's instructions are reaching Claude Code and not Codex right now.**
That is the single most consequential thing we found while planning, it is P1, and it is the first
thing we are fixing — as a quick-task ahead of the epic, because it is bounded to the dialect layer.
The fix is to fold the instructions into the turn's prompt for a dialect that maps no flag, named
rather than prefixed unmarked, and to stop reporting them as unmapped once they are actually
delivered.

---

## What we are building, in order

Epic 0011, phases numbered from 59 so no transferred ID is reused. Every phase is contract
**additions** — a minor bump, a *Pins* row, protocol 3 unchanged throughout.

| | What | Your asks |
|---|---|---|
| **Q1** | instructions reach a dialect with no flag | 4 (the gap above) |
| **59** | a change is legible on the record | **1**, 6 |
| **60** | the write-class toolset completes | **2** |
| **61** | undo and an agent's own workspace | **3**, 7 |
| **62** | what a run carries into any provider | **5**, 11, rest of 4 |
| **63** | visible and steerable | 8, 9 |

**Why this order, and it is mostly yours.** 59 is first because it is your #1 and because 61 cannot
be designed without it — a snapshot has to know what it must hold, which is exactly the dependency
your item 6 and item 7 have between them. 60 comes after 59 because a cross-file patch whose record
lies about what happened is worse than no patch at all.

**Your answer on ask 1 settled our open question**, so thank you: content up to a cap, `truncated`
beyond it, no per-file version history because git keeps that. That is what we are building. The
cap's value and where it lives is phase 59's first decision.

**On ask 2 — both, confirmed carried.** You said the patch and the background shell both cost you;
that was the answer we needed. Phase 60 does both, each as an operation with an honest effect
profile so every mode judges it like the nine that exist.

**On ask 3 — your narrowing decided the design.** We asked whether the kit should ship one
mechanism, a port with a git-backed adapter, or only the record of what would be restored. You said
a git-backed adapter where a root is a work tree covers your first use case, so that is what phase
61 builds — a port, with the refuse-not-crash default our own rules require of a new port. A restore
is itself an act: effects, the mode's judgement, on the record. An undo that bypasses governance is
a hole, and we are not shipping one.

**On ask 5 — and we will re-measure.** You asked for the ENH-012 sentinel re-run against claude
**2.1.284** rather than inferred from 2.1.235. Agreed and scheduled into phase 62; BUG-031 is the
precedent for why inferring across a CLI version gap is not good enough. ENH-047 lands as a
component **a plugin switches on**, not a default — the existing default, that a governed CLI does
not read a folder's instruction files, stays.

**On ask 11 — probably not needed, tell us.** You said you would use `DirectorySkills` if it already
parses `SKILL.md`. It does not — it reads `*.toml` only. So this is real work, it is optional, and
we will skip it unless you say otherwise.

## Two we are not scheduling, and why

- **Ask 10 — credential injection.** We cannot build this until the vault and the egress proxy have
  a home. D137 already names an egress proxy with an allowlist as a later seam; where it lives — kit,
  or product and infrastructure — is your §5 "to agree", and it is still to agree. Nothing blocks
  you meanwhile; say where it lands and we will scope it.
- **Ask 12 — Phase 54 triggers.** Parked on your side pending initiative 0055 and the owner's
  hands-free decision. We are not pre-empting that.

## What we need from you

1. **Nothing to unblock asks 4 and 6** — use `store_skills`, pass your own `SinkPort` instead of
   `KeepingSink`, and your database is already a skill source. That is the point of this reply
   arriving before the code.
2. **Confirm the Codex instruction gap against your build** — read `unmapped_behaviour` on a Codex
   thread. If you see `system` there, your Build agent has been running without its instructions on
   Codex, and you will want to know that before Q1 lands rather than after.
3. **Say whether ask 11 is still wanted** now that you know `DirectorySkills` does not parse
   `SKILL.md`.
4. **Say where the vault and egress proxy live** when you have decided, and ask 10 gets scoped.
5. **Lane H's row on the board is going stale.** This epic is one repository by the owner's
   instruction, and the board is in another, so we are not writing it. Please carry lane H's line
   for Epic 0011 yourselves, or tell us to stop maintaining it.

**On evidence, in the same spirit as last time.** Every phase here runs the full gate — ruff, ruff
format, mypy strict, the whole suite — and TDD is strict in this repository, so each group starts
red. For Q1 and phase 62 specifically, a green unit suite does **not** prove instructions reached a
model, so each of those carries at least one live measurement against the real CLI. We will tell you
what we measured and on which CLI version, not just that it was green.
