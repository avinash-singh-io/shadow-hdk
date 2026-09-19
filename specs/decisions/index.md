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
| D54 | a skill is a registry entry that says what it is for and where it came from | [`phases/phase-24-the-skill-registry/history.md`](/phases/phase-24-the-skill-registry/history.md) |
| D55 | the registry is a component, so choosing is a step on the record and reaches every host | [`phases/phase-24-the-skill-registry/history.md`](/phases/phase-24-the-skill-registry/history.md) |
| D56 | minting proposes; keeping is the host's | [`phases/phase-24-the-skill-registry/history.md`](/phases/phase-24-the-skill-registry/history.md) |
| D57 | a component may ask for itself, and the run parks on it | [`adhoc/harden-to-24/record.md`](/adhoc/harden-to-24/record.md) |
| D58 | a step that cannot park asks the host live | [`adhoc/harden-to-24/record.md`](/adhoc/harden-to-24/record.md) |
| D59 | a question says what it is about | [`adhoc/studio-scenarios/record.md`](/adhoc/studio-scenarios/record.md) |
| D60 | a connection's death is that connection's problem | [`adhoc/studio-scenarios/record.md`](/adhoc/studio-scenarios/record.md) |
| D61 | the record speaks the industry's words | [`phases/phase-25-the-hosts-controls/history.md`](/phases/phase-25-the-hosts-controls/history.md) |
| D62 | a thread is turns, and a turn is a run | [`phases/phase-25-the-hosts-controls/history.md`](/phases/phase-25-the-hosts-controls/history.md) |
| D63 | the record is complete; the activity is live | [`phases/phase-25-the-hosts-controls/history.md`](/phases/phase-25-the-hosts-controls/history.md) |
| D64 | a mode is a policy, a behaviour and a presentation — data, live | [`phases/phase-25-the-hosts-controls/history.md`](/phases/phase-25-the-hosts-controls/history.md) |
| D65 | "approve and add a rule" is a rule the person makes; the agent's question is an item | [`phases/phase-25-the-hosts-controls/history.md`](/phases/phase-25-the-hosts-controls/history.md) |
| D66 | one `Store` port, and every registry reads it live | [`phases/phase-25-the-hosts-controls/history.md`](/phases/phase-25-the-hosts-controls/history.md) |
| D67 | the thread, the handles, the store and the composition cross the wire; a thread's offer is held by one task | [`phases/phase-26-any-language/history.md`](/phases/phase-26-any-language/history.md) |
| D68 | the TypeScript types are generated by json-schema-to-typescript, one module per contract, held by an invariant | [`phases/phase-26-any-language/history.md`](/phases/phase-26-any-language/history.md) |
| D69 | the studio is a page `serve` itself serves; a session's threads close with it | [`phases/phase-26-any-language/history.md`](/phases/phase-26-any-language/history.md) |
| D70 | a battery is a file — an MCP server or a callable consumed behind the component port, its effects vouched for | [`phases/phase-27-batteries-and-the-facade/history.md`](/phases/phase-27-batteries-and-the-facade/history.md) |
| D71 | one package is the host's front door — `Harness` in `shadow-hdk-serve`, three lines by default, one step deeper without leaving it | [`phases/phase-27-batteries-and-the-facade/history.md`](/phases/phase-27-batteries-and-the-facade/history.md) |
| D72 | the optimiser is a port over documents with slots, gated by the sink; its evaluator is locked before any loop | [`phases/phase-27-batteries-and-the-facade/history.md`](/phases/phase-27-batteries-and-the-facade/history.md) |
| D73 | the registries are the harness's answer — `Thread.tools()`, `tools/list`, `skills/list` | [`phases/phase-28-the-workspace/history.md`](/phases/phase-28-the-workspace/history.md) |
| D74 | a child run is judged in its parent's context | [`phases/phase-28-the-workspace/history.md`](/phases/phase-28-the-workspace/history.md) |
| D75 | the `ask` mode; a run's tool surface is exactly the registry | [`phases/phase-28-the-workspace/history.md`](/phases/phase-28-the-workspace/history.md) |
| D76 | the workspace is one or many roots, chosen per thread and added live; the environment and the provider follow the mode | [`phases/phase-28-the-workspace/history.md`](/phases/phase-28-the-workspace/history.md) |
| D77 | one rule, one implementation — a session leader started in one place, frames split in one place, a root's name a rule rather than a guess | [`phases/phase-28-the-workspace/history.md`](/phases/phase-28-the-workspace/history.md) |
| D78 | one distribution, `shadow-hdk`, with extras — the parts stay parts, ship as one wheel; `[all]` is everything; amends D9 | [`adhoc/2026-09-13-one-distribution/record.md`](/adhoc/2026-09-13-one-distribution/record.md) |
| D79 | the record chooses its store — `[store] url` (sqlite or Postgres) fills the Store, the ThreadStore and the checkpointer at once; a host hands its own three in | [`phases/phase-29-one-app-server/history.md`](/phases/phase-29-one-app-server/history.md) |
| D94 | sessions that idle out (`idle_seconds`); a stream that survives a drop — frame ids, a grace, reattach with `Last-Event-ID` and replay | [`phases/phase-30-a-product-owns-what-it-owns/history.md`](/phases/phase-30-a-product-owns-what-it-owns/history.md) |
| D93 | a parked run behind a port of ours — `RunStore` (four methods) with the library's saver over it; `ThreadRecord.version` | [`phases/phase-30-a-product-owns-what-it-owns/history.md`](/phases/phase-30-a-product-owns-what-it-owns/history.md) |
| D92 | governance composed by routing (`Routed`); refusals typed — `error.data.kind` from `ERROR_KINDS`, the TypeScript client's `RemoteError` | [`phases/phase-30-a-product-owns-what-it-owns/history.md`](/phases/phase-30-a-product-owns-what-it-owns/history.md) |
| D91 | the contracts ship — `shadow_hdk.testing.contracts` and `.providers.ScriptedAgent`; `Questions` a kernel port the runtime asks through, `Approvals` one implementation | [`phases/phase-30-a-product-owns-what-it-owns/history.md`](/phases/phase-30-a-product-owns-what-it-owns/history.md) |
| D90 | tokens and running time on the record — `Spent.input_tokens/output_tokens/unmetered`; a thread's seconds are its turns' running time, the meter paused between turns | [`phases/phase-30-a-product-owns-what-it-owns/history.md`](/phases/phase-30-a-product-owns-what-it-owns/history.md) |
| D89 | the agent streams — `AgentComponent` through `ModelPort.stream`, deltas as activity, the response assembled; `LangChainModel.stream` merges chunks and keeps thinking (ENH-065) | [`phases/phase-30-a-product-owns-what-it-owns/history.md`](/phases/phase-30-a-product-owns-what-it-owns/history.md) |
| D88 | a park on purpose — `Parked` as an answer, `turn(on_question="park")`; the turn ends `parked`, the question on the record, `settle` later | [`phases/phase-30-a-product-owns-what-it-owns/history.md`](/phases/phase-30-a-product-owns-what-it-owns/history.md) |
| D87 | the governed turn as a primitive — `Conversation`, one provider session and its turns without the record; `Thread` is a `Conversation` plus a record, a store and a hold | [`phases/phase-30-a-product-owns-what-it-owns/history.md`](/phases/phase-30-a-product-owns-what-it-owns/history.md) |
| D86 | operations — `/healthz` without a bearer, the version in `initialize`, `admin/sessions` and `admin/threads`; the per-run token closed: one bearer, the identity on the thread | [`phases/phase-29-one-app-server/history.md`](/phases/phase-29-one-app-server/history.md) |
| D85 | the rules the field has — `ask` as a decision; deny, ceiling, ask, mode, allow, in that order; the strongest matching rule decides; patterns in a rule's inputs anchored to a root | [`phases/phase-29-one-app-server/history.md`](/phases/phase-29-one-app-server/history.md) |
| D84 | the budget on the record — `thread/start {budget}`, `ThreadRecord.budget` and `.spent`; the meter starts from the record at every opening (closes ENH-013) | [`phases/phase-29-one-app-server/history.md`](/phases/phase-29-one-app-server/history.md) |
| D83 | batteries live — `[tools] batteries` seeds the store's `wanted` rows; the rows say which batteries the next thread gets, opened and closed at the host without a restart | [`phases/phase-29-one-app-server/history.md`](/phases/phase-29-one-app-server/history.md) |
| D82 | identity on the thread, scope on the rows — `thread/start {principal, attributes}` on the record and every judgement; `scope` on rules and modes (`in_scope`), registries answering in scope; a card's rule is the answerer's | [`phases/phase-29-one-app-server/history.md`](/phases/phase-29-one-app-server/history.md) |
| D81 | one thread, one holder — a lease on the ThreadStore, renewed while open, lapsing when the holder dies; `turn/start {when}`: enqueue · reject · interrupt | [`phases/phase-29-one-app-server/history.md`](/phases/phase-29-one-app-server/history.md) |
| D80 | a parked turn survives the host — the open question on the record, the served thread on the host's checkpointer, `parked` on resume, `settle` runs the act from its checkpoint and tells the agent | [`phases/phase-29-one-app-server/history.md`](/phases/phase-29-one-app-server/history.md) |
| D95 | one Shadow umbrella, with HDK construction and ready-to-run Harness surfaces over the same public contracts | [`epics/0008-production-boundary.md`](/epics/0008-production-boundary.md) |
| D96 | capability, requirement and evidence are different types; unknown never satisfies an explicit requirement | [`epics/0008-production-boundary.md`](/epics/0008-production-boundary.md) |
| D97 | provider truth, environment truth and execution authority stay separate | [`epics/0008-production-boundary.md`](/epics/0008-production-boundary.md) |
| D98 | model and CLI providers meet behind one durable AgentPort and Thread surface | [`epics/0008-production-boundary.md`](/epics/0008-production-boundary.md) |
| D99 | approval is consent evidence; a separate single-use host authorization permits an irreversible act | [`epics/0008-production-boundary.md`](/epics/0008-production-boundary.md) |
| D100 | principal, workspace, policy, registry, provider configuration and mode form explicit revisioned authority | [`epics/0008-production-boundary.md`](/epics/0008-production-boundary.md) |
| D101 | a controlled irreversible effect is `stage -> authorize -> execute -> reconcile` | [`epics/0008-production-boundary.md`](/epics/0008-production-boundary.md) |
| D102 | an effect authorization binds the exact stage, authority, identity, expiry, key, run and step and is consumed once | [`epics/0008-production-boundary.md`](/epics/0008-production-boundary.md) |
| D103 | uncertainty is a first-class outcome; an executing non-idempotent effect is never blindly retried | [`epics/0008-production-boundary.md`](/epics/0008-production-boundary.md) |
| D104 | the append-only run/effect journal is authoritative; mutable records and UI are folds | [`epics/0008-production-boundary.md`](/epics/0008-production-boundary.md) |
| D105 | the HDK event vocabulary remains generic and excludes adopter-owned concepts | [`epics/0008-production-boundary.md`](/epics/0008-production-boundary.md) |
| D106 | open standards meet Shadow at adapters rather than dictating the kernel model | [`epics/0008-production-boundary.md`](/epics/0008-production-boundary.md) |
| D107 | a plan is a `Composition`; a harness is data; no new grammar | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D108 | admission is whole-plan judgement, not authorization — structural → existence → effects, the mismatch list complete; Phase 33 still at the act | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D109 | limits are order-bearing values narrowing host → mode → parent by `meet`, carried on the mode as live data; the lease is the floor | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D110 | planning is a registered component; the loop's `compose` meta-tool is sugar over it | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D111 | a refused plan is an observation; the planner re-proposes; the runtime never trims a proposal | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D112 | a plan may run after its planner — a pattern field | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D113 | a harness is a component: its profile the `meet` of its parts; admitted recursively; parameters bound at instantiation | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D114 | a blueprint carries requirements and limits, never capabilities, credentials, tenant data or standing authority; selection and admission re-run at every instantiation | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D115 | a run request is durable and idempotent; the scheduler owns timing, consumed behind a port, never authority | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D116 | amend is a host handle on the record; admission applies to the amendment | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D117 | deps re-derived: 36 needs 33 only; 34 exists for the blueprint layer; 35 is orthogonal and later | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D118 | a harness is a distribution that ships with its runtime pinned inside; never a separate runtime to operate | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D119 | one runtime, many language surfaces — generated client, port stubs and scaffold per language; a native runtime elsewhere is a non-goal until an adopter needs it and the contracts are stable across two releases | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D120 | a harness runs on the Shadow runtime; export encodings are adapters; compile-to-X only when the field shares a target format | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D121 | one question for the plan: an `Ask` at admission parks the plan as a single question; the acts inside still get their Phase 33 grants | [`epics/0009-the-harness-as-data.md`](/epics/0009-the-harness-as-data.md) |
| D122 | layers decide separately: the OS layer native per OS; the ecosystem Python; the engine's language a dated decision | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D123 | the OS layer's native parts are small static helper executables from one Rust crate, invoked by the Python leash; policy and the proof stay in Python; no PyO3 required | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D124 | one contract, native primitives: POSIX process groups · Job Objects; seatbelt · Landlock+seccomp (bwrap fallback) · restricted tokens — never "POSIX and hope" | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D125 | proof before claim, per OS: no confined mode opens unproven; refuse with `CannotEnforce`, never a silent `full` — stricter than Claude Code's default, equal to its hard mode | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D126 | same semantics on three OSes, proven by the same suites on three CI runners; a red runner blocks the release | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D127 | one artifact per OS/arch, no prerequisite, PyApp fully embedded; the server a container image; size and start time measured against the field's ~100 MB norm | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D128 | the engine and the ecosystem are unchanged by this epic: LangGraph stays; no engine code in Rust; the facade signatures unchanged | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D129 | B (a native engine) is a dated decision at the close of Epic 0009, no later than 2026-12-31, on the LangGraph ledger, the artifact's measurements and Windows proof status | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D130 | the record is the source of truth; a checkpoint is a view: Phase 37 builds on the `RunStore` port, never on LangGraph's checkpoint classes | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D131 | release keys stay outside the tree; signable artifacts; every nested Mach-O signed with hardened runtime on macOS | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D132 | development on Python 3.14; consumers keep `>= 3.12`; the artifact pins the interpreter the matrix proves | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D133 | Linux confinement is Landlock + seccomp in-process by the helper, bubblewrap the fallback, the proof deciding which is in force | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D134 | Windows ships in two steps: process control and honest `full` first; confinement by the elevated model or WSL2, decided in Phase 43 with evidence; no unelevated ACL prototype | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D135 | consume the OS primitives (`landlock`, a Job-Object crate, `windows-rs`, PyApp); own the proof | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D136 | `sandbox-exec`'s deprecation is an accepted, detected risk: the proof fails closed the day it goes | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D137 | named seams left for later: network egress through a proxy with an allowlist; cloud confinement as a microVM backend | [`epics/0010-cross-platform.md`](/epics/0010-cross-platform.md) |
| D138 | a reach from the serving process is an egress channel: the confined ceilings say `contained`, `read-only`'s corrected; the door for web reads is a product mode with `ask_above.contained = true` | [`phases/phase-45-truth-both-ways/history.md`](/phases/phase-45-truth-both-ways/history.md) |
| D139 | a turn's failure is typed on the record (`TurnRecord.failure`) and raised typed (`SessionGone`); the wire kind `session_gone`; how a CLI says it is a provider-file value | [`phases/phase-45-truth-both-ways/history.md`](/phases/phase-45-truth-both-ways/history.md) |
| D140 | a turn's words are the turn's: `turn(attributes=)` merges for that turn's judgements and is never written back; `resume(attributes=)` replaces the record's | [`phases/phase-45-truth-both-ways/history.md`](/phases/phase-45-truth-both-ways/history.md) |
| D141 | unknown, never zero, for cache tokens: `Usage.cache_read_tokens`/`cache_write_tokens` are `None` where unreported; `Spent` counts them | [`phases/phase-45-truth-both-ways/history.md`](/phases/phase-45-truth-both-ways/history.md) |

## Also here

* [`0000-template.md`](/decisions/0000-template.md) — the shape a longer record takes when one is
  needed. The numbered ADRs the roadmap refers to are the owner's and none is written yet.
* [`impact-map.md`](/decisions/impact-map.md) — topic keywords to spec files.
