---
type: Phase
phase: 24
name: the-skill-registry
epic: 0013-the-skill-registry
status: complete
topics: [skills, registry, progressive-disclosure, self-evolution, sink, d17]
deps: [phase-23-a-host-in-any-language]
---

# Phase 24 — The skill registry

A skill today is a file the host loads and hands to one agent: `Skill(name, prompt, needs)`,
checked against `visible()` before the first turn (D17). That is a directory, and a directory has
three things wrong with it for a harness that is supposed to be generic and to grow while it runs.
The model cannot *choose* a skill — the host chose one for it. Nothing an agent works out during a
run can become a skill without a person editing a file. And every skill's whole prompt would have
to be in the catalogue for the model to know it exists.

This phase makes skills a **registry** with three sources and one act of keeping:

**Predefined.** Skills shipped as TOML, the way providers are (D40): a small library of *generic*
procedures — none of them about code — and any directory a host points at.

**Minted.** An agent that works out a procedure worth repeating writes it down mid-run with a
meta-tool. It lives for the run and is usable at once, by this agent and any it spawns.

**Proposed for keeping.** Minting also *proposes* the skill through the sink as
`Proposal(kind="skill")`. The runtime keeps nothing; the host decides whether that proposal becomes
a kept skill and hands its kept skills back as a source next run. Self-evolution is a governed act
with a record, and promotion is the host's decision, never the runtime's.

**Progressive disclosure, one mechanism.** A skill costs the model a name and a line until it is
chosen — the same thinning Phase 21 built for a large catalogue of tools (D13), used for a second
kind of thing rather than built twice. The registry is offered as a **component**: `use_skill`
carries the names and lines on its own description, and choosing is a governed step on the record
— reachable in-process, over the wire, and by a CLI through the registry socket alike (D55). It is
where the D17 check runs.

## What this phase makes true

- A `Skill` has a `description` — the one line — and says where it came from.
- A `SkillRegistry` is a union of sources; the agent adapter offers its names and lines in the
  catalogue and reveals a body only on `use_skill`, after `missing_for` against `visible()`.
- `mint_skill` mints for the run and proposes for keeping; a sink that keeps it can hand it back.
- A skill is not a permission (D17 stands): using one grants nothing; every effect is still judged.
- The examples show it: the host example lists its skills and keeps a minted one in its ledger.

## What this phase does not do

Promotion policy — which proposals a host keeps, who may mint — is the host's. A skill that runs
*code* is Phase 25's Code Mode. Skills shared between hosts is Phase 26.
