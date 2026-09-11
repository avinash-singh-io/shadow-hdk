---
type: Plan
phase: 24
---

# Plan — Phase 24

## Group 1 — a skill says what it is, and where it came from

- `Skill` gains `description: str` (one line; required — a skill nobody can find is a file) and
  `source: str` (`shipped`, `minted`, or the name a host gives its own source).
- `KEYS` and `skill_from` accept the new keys; every existing TOML in tests gains a line.
- `SkillSource` protocol: `async def skills(self) -> Sequence[Skill]`. `DirectorySkills(path)`
  reads every `*.toml` under a directory; `MintedSkills()` is the run's own, empty at start.
- `SkillRegistry(sources)`: `listing()` — names and lines; `find(name)`; a later source shadows an
  earlier one by name and the record says so.

## Group 2 — the model sees names and lines; `use_skill` reveals and checks

- `Pattern.meta_tools` may include `USE_SKILL` and `MINT_SKILL`; interfaces in `meta.py`.
- The catalogue's system text gains a *Skills* section: one line each, always thin — the body is
  the point of the disclosure. `describe(name)` answers for a skill as for a tool (the body and
  its needs), from the registry.
- `use_skill(name)`: `missing_for(skill, visible())`; unmet → the tool answer names what is
  missing and the skill is **not** loaded; met → the body arrives as the tool's answer, and the
  skill is noted in the transcript as in use. Nothing is granted.

## Group 3 — minted, and proposed for keeping

- `mint_skill(name, description, prompt, needs)`: added to the run's `MintedSkills`, usable at
  once by this agent; **and** `ctx.propose(Proposal(kind="skill", payload=…, provenance=…))` —
  the same move as `compact` (D18): the adapter writes nowhere.
- A child spawned after a mint sees it: minted skills ride the pattern's registry, and the
  registry the child gets is the parent's (in-process); over the wire the agent runs host-side,
  so nothing new crosses.
- A test sink keeps `kind="skill"` proposals and hands them back as a source; the second run
  finds the skill under `source="kept"`.

## Group 4 — shipped, generic

- `packages/adapters/agent/src/shadow_hdk/adapters/agent/library/*.toml`: a few procedures
  that make sense for *any* agent — look before you change; verify before you say done; when
  a result is large, page it (D47's `recall`); ask when the brief is ambiguous. `shipped()`
  returns them as `DirectorySkills`.
- The host example: `--skills=DIR` adds a directory; the ledger keeps `kind="skill"` proposals and
  the next run hands them back. The coder example lists shipped skills to the provider's brief.

## Group 5 — invariants, parity, documents

- The documents invariant: `architecture/adapters.md` names the registry; `decisions/index`.
- `test_the_wire_is_at_parity` unchanged — the agent runs host-side; assert nothing new crosses.
- D54–D56 in history; 0.18.0 (a `Skill` with two new fields and a `Pattern` with two new verbs
  is an adapter contract change; D9 moves every package).
