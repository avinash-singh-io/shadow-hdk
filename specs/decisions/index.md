---
type: Index
---

# Decisions

**Every decision this runtime has taken, and where it is written down.**

This directory holds the template and this map, and **not the decisions themselves** — that is
deliberate (TD-008). A decision belongs beside the work that forced it: D36 is only legible next to
the fake `runsc` that provoked it, and D38 next to the transcript that showed a policy overruling a
human. Copying them here would produce a second version of each to keep in step, which is the
disease this row is about rather than a cure for it.

What was wrong is that nothing pointed at them, so `CLAUDE.md`'s *why was X chosen* sent a reader to
a folder holding a template. It points here now, and this table is generated from the documents
rather than remembered.

| | Decision | Where |
|---|---|---|
| D1 | The agent loop is a component, not a second entry point | [`architecture/decisions.md`](/architecture/decisions.md) |
| D2 | Spawning is ambient | [`architecture/decisions.md`](/architecture/decisions.md) |
| D3 | The model's meta-tools belong to the pattern, not the runtime | [`architecture/decisions.md`](/architecture/decisions.md) |
| D4 | `Ports` and `RunOptions` are runtime types, not kernel types | [`architecture/decisions.md`](/architecture/decisions.md) |
| D5 | Ask and Await are `interrupt()` | [`architecture/decisions.md`](/architecture/decisions.md) |
| D6 | Events go two ways at once | [`architecture/decisions.md`](/architecture/decisions.md) |
| D7 | A component raising is data; a port raising is a failure | [`architecture/decisions.md`](/architecture/decisions.md) |
| D8 | Test doubles ship in the package | [`architecture/decisions.md`](/architecture/decisions.md) |
| D9 | Versioning and the pin | [`architecture/decisions.md`](/architecture/decisions.md) |
| D10 | LangGraph `>=1.2,<2`; Python `>=3.12` | [`architecture/decisions.md`](/architecture/decisions.md) |
| D11 | Latency is a budget with a benchmark, not an aspiration | [`architecture/decisions.md`](/architecture/decisions.md) |
| D12 | Build versus buy: LangGraph executes; we compile and govern | [`architecture/decisions.md`](/architecture/decisions.md) |
| D13 | Tools scale by scoping, not by a bigger list | [`architecture/decisions.md`](/architecture/decisions.md) |
| D14 | a port may grow a method, with a default | [`phases/phase-1-real-adapters/history.md`](/phases/phase-1-real-adapters/history.md) |
| D15 | cancellation is a handle the host holds, checked where the lease is checked | [`phases/phase-6-the-compiler-complete/overview.md`](/phases/phase-6-the-compiler-complete/overview.md) |
| D16 | a held child is a parked run, not a resident object | [`phases/phase-7-sub-agents/overview.md`](/phases/phase-7-sub-agents/overview.md) |
| D17 | patterns and skills are TOML, and the loader refuses what it cannot check | [`phases/phase-8-patterns-skills-replay/overview.md`](/phases/phase-8-patterns-skills-replay/overview.md) |
| D18 | compaction is a meta-tool, which is what "not a runtime power" means | [`phases/phase-8-patterns-skills-replay/history.md`](/phases/phase-8-patterns-skills-replay/history.md) |
| D19 | the graph's state holds JSON, not our classes | [`phases/phase-9-the-wire/overview.md`](/phases/phase-9-the-wire/overview.md) |
| D20 | `Spent`, the eleventh event kind: what a step cost, said out loud | [`phases/phase-9-the-wire/overview.md`](/phases/phase-9-the-wire/overview.md) |
| D21 | a component that crosses still needs a context, and the host binds one | [`phases/phase-9-the-wire/history.md`](/phases/phase-9-the-wire/history.md) |
| D22 | The port set is open. Six is a count, not a constraint | [`architecture/decisions.md`](/architecture/decisions.md) |
| D23 | a rule selects by name, never by predicate | [`phases/phase-10-effect-rules/overview.md`](/phases/phase-10-effect-rules/overview.md) |
| D24 | the check runs on the rules, not on the run | [`phases/phase-10-effect-rules/overview.md`](/phases/phase-10-effect-rules/overview.md) |
| D25 | containment is proven at construction, and refused if it cannot be | [`phases/phase-11-contained-sandboxes/overview.md`](/phases/phase-11-contained-sandboxes/overview.md) |
| D26 | a ground is data, and the engine is its only interpreter | [`phases/phase-12-derivation/overview.md`](/phases/phase-12-derivation/overview.md) |
| D27 | a driver is trusted by a signature over what it declares, checked when it registers | [`phases/phase-13-effect-leases/overview.md`](/phases/phase-13-effect-leases/overview.md) |
| D28 | telemetry carries the shape of a run, never its payloads | [`phases/phase-14-telemetry/overview.md`](/phases/phase-14-telemetry/overview.md) |
| D29 | the world is a scope; a device is a component with a posture, not a port | [`phases/phase-15-environment-contract/overview.md`](/phases/phase-15-environment-contract/overview.md) |
| D30 | posture is on the record and in front of governance | [`phases/phase-15-environment-contract/overview.md`](/phases/phase-15-environment-contract/overview.md) |
| D31 | one device contract, three roles, the fake first | [`phases/phase-15-environment-contract/overview.md`](/phases/phase-15-environment-contract/overview.md) |
| D32 | the envelope is the payload; the transport's version is not the contract's business | [`phases/phase-16-mqtt/overview.md`](/phases/phase-16-mqtt/overview.md) |
| D33 | what a run has spent rides in the checkpoint; parked time is not spent | [`phases/phase-17-the-audit/history.md`](/phases/phase-17-the-audit/history.md) |
| D34 | a wire session owns a checkpointer; the callback timeout is the wire's | [`phases/phase-17-the-audit/history.md`](/phases/phase-17-the-audit/history.md) |
| D35 | a step owns the process tree it starts | [`phases/phase-18-the-p1s/history.md`](/phases/phase-18-the-p1s/history.md) |
| D36 | containment is proven by what is denied, never by what is announced | [`phases/phase-18-the-p1s/history.md`](/phases/phase-18-the-p1s/history.md) |
| D37 | a parent that parks comes back holding its children | [`phases/phase-18-the-p1s/history.md`](/phases/phase-18-the-p1s/history.md) |
| D38 | a parked step resumes where it parked — in progress, not from the top | [`phases/phase-18-the-p1s/history.md`](/phases/phase-18-the-p1s/history.md) |
| D39 | inference and agency are two seams, not one interface | [`phases/phase-20-providers/history.md`](/phases/phase-20-providers/history.md) |
| D40 | a provider is data, like a pattern | [`phases/phase-20-providers/history.md`](/phases/phase-20-providers/history.md) |
| D41 | the harness asks; it never reads a credential and never installs | [`phases/phase-20-providers/history.md`](/phases/phase-20-providers/history.md) |
| D42 | the socket — every effect routes through the run's registry | [`phases/phase-20-providers/history.md`](/phases/phase-20-providers/history.md) |
| D43 | the loop stays theirs, and that is the price on the label | [`phases/phase-20-providers/history.md`](/phases/phase-20-providers/history.md) |
| D44 | the registry is connected to, never launched | [`phases/phase-20-providers/history.md`](/phases/phase-20-providers/history.md) |
| D45 | thinking is on the record, beside what it led to | [`phases/phase-21-the-visible-agent/history.md`](/phases/phase-21-the-visible-agent/history.md) |
| D46 | the stream folds into steps, once, and the fold crosses the wire folded | [`phases/phase-21-the-visible-agent/history.md`](/phases/phase-21-the-visible-agent/history.md) |
| D47 | a large result is held by the agent, never written by the runtime | [`phases/phase-21-the-visible-agent/history.md`](/phases/phase-21-the-visible-agent/history.md) |
| D48 | an environment is where effects land, and it has a mode | [`phases/phase-22-the-environment/history.md`](/phases/phase-22-the-environment/history.md) |
| D49 | local execution is confined by the operating system, and proven first | [`phases/phase-22-the-environment/history.md`](/phases/phase-22-the-environment/history.md) |
| D50 | an isolated environment sits behind a Box, proven by two denials | [`phases/phase-22-the-environment/history.md`](/phases/phase-22-the-environment/history.md) |
| D51 | the agent runs where the record is, whichever side of the wire that is | [`phases/phase-23-a-host-in-any-language/history.md`](/phases/phase-23-a-host-in-any-language/history.md) |
| D52 | nothing reaches a run's registry without the token it minted | [`phases/phase-23-a-host-in-any-language/history.md`](/phases/phase-23-a-host-in-any-language/history.md) |
| D53 | a provider's child dies with the process that held it, whatever ended it | [`phases/phase-23-a-host-in-any-language/history.md`](/phases/phase-23-a-host-in-any-language/history.md) |

## Also here

* [`0000-template.md`](/decisions/0000-template.md) — the shape a longer record takes when one is
  needed. The numbered ADRs the roadmap refers to are the owner's and none is written yet.
* [`impact-map.md`](/decisions/impact-map.md) — topic keywords to spec files.
