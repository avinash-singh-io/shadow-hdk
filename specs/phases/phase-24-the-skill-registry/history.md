---
type: History
phase: 24
---

# History — Phase 24

### [DECISION] 2026-09-11 — D54: a skill is a registry entry that says what it is for and where it came from

Topics: skills, registry, provenance, d17
Affects-phases: phase-24-the-skill-registry
Affects-specs: architecture/adapters.md#the-agent-adapter, architecture/file-structure.md

A skill was a file the host loaded and handed to one agent (D17). That is a directory: the model
could not choose, nothing an agent worked out mid-run could become one without a person editing a
file, and every body would have had to be in the catalogue for the model to know it existed.

A `Skill` now carries a `description` — the one line the model chooses by; required in a file,
because a body alone is a prompt and not an entry, optional for a `Skill` a host constructs in code
— and a `source`: `shipped`, `file`, `minted`, `kept`, or whatever a host names its own. A
procedure a team reviewed and a procedure a model wrote mid-run are different kinds of claim, and
the record tells them apart. `SkillRegistry` is a union of `SkillSource`s — `DirectorySkills`,
whatever the host hands in, and `minted`, always last — later shadowing earlier by name, with what
was shadowed kept: a skill changing under the model's feet is never silent. A registry is itself a
source, so a host composes one from another. Four shipped skills, none about code.

*Why:* the harness is generic and grows while it runs; a directory cannot. *Overturned by:* a
kind of skill that is not a prompt plus needs — Phase 25's Code Mode may be one, and it will say.

---

### [DECISION] 2026-09-11 — D55: the registry is a component, so choosing is a step on the record and reaches every host

Topics: skills, component, disclosure, wire, subscription, d13
Affects-phases: phase-24-the-skill-registry
Affects-specs: architecture/adapters.md#the-agent-adapter

The first cut made `use_skill` and `mint_skill` meta-tools of the in-process loop, beside
`describe` and `compact`. Eight mutants killed, and it was wrong: a meta-tool lives in the
transcript and nowhere else, so a person watching agent steps never saw a skill being chosen; and
it was out of reach of an agent on the far side of the wire and of a CLI by subscription, which is
the host this lane exists for. Two mechanisms for one act is what principle 5 is against.

`SkillComponents` registers `use_skill` as a tool like any other. It is **pure**, so any mode that
lets the agent see anything lets it choose. The names and lines ride the tool's own description
and its `enum`, rebuilt on every `registrations()` — which `visible()` asks for on every catalogue
— so a skill minted a turn ago is there the next; this *is* Phase 21's thinning, name and line
until chosen, for a second kind of thing. Choosing runs D17's check against `visible()`: refused
by name, the body never arrives. Chosen, it arrives as the tool's answer and the choice is an
`Invoked`/`Observed` pair on the record, nested where it happened.

Measured live through the coder: Claude Code chose `look-before-you-change` over the registry
socket and followed it — read before write, the smallest change, verified by re-reading.

*Why:* act through components, record through the sink; a thing chosen is an act. *Overturned
by:* a provider that cannot take a tool at all — then it cannot take any of this run's tools
either, and skills are the least of it.

---

### [DECISION] 2026-09-11 — D56: minting proposes; keeping is the host's

Topics: skills, minting, sink, self-evolution, d18
Affects-phases: phase-24-the-skill-registry
Affects-specs: architecture/adapters.md#the-agent-adapter

`mint_skill` is offered only where the host says `minting=True`, and declares `writes: {record}`,
reversible — so a mode that permits no writes hides it by effect, and the policy never has to hear
of minting. It checks the shape the way a file is checked (a name, a line, a body), adds the skill
to the registry's `minted` source — usable at once, by this agent and any that shares the
registry — and **proposes** it through the sink as `Proposal(kind="skill")`, the shape `compact`
already has (D18). The adapter writes nowhere. Self-evolution is a governed act with a record.

Promotion is the host's: `kept_from(proposal)` turns a proposal it kept into a `Skill` with the
host's own source name, checked again because a proposal is data from a run. The host example's
ledger is a source — everything minted is kept, the simplest policy; a real host reviews, or asks.

*Why:* the runtime keeps nothing (`09` §6) and grants nothing (D17). *Overturned by:* a host that
wants the runtime to keep skills — it should hand in a source instead, and it can.

---

### [NOTE] 2026-09-11 — what moved

Topics: examples, policy, record
Affects-phases: phase-24-the-skill-registry

The host example's policy allows writes to `{workspace, record}` rather than the workspace alone:
a proposal into the host's own ledger is the host's to receive. Found because `mint_skill`'s
first run asked the host whether the run might write to the record — the policy being right by
its own rule, and the rule being one scope short. The coder's confined mode permits record
writes for the same reason; `read-only` still hides minting. A fifth condition the arrangement
had not created — a pattern granting minting to a role with no registry — became a test before
the meta-tool form was replaced, and the equivalent for the component form (`minting=False`) is
one now.

---
