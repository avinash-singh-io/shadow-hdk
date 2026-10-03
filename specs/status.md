---
type: Status
---

# Project Status

> **2026-10-04 — 0.47.0 candidate verified, not published.** D adds stored human-readable descriptions
> to the existing agent chooser reply, preserving the absent-field fallback and role instructions.
> Full gate: 2,254 passed, 8 skipped; lint/format/types clean. Six new cases pass on the installed
> wheel outside checkout; seven mutation checks bite. Earlier candidates are frozen
> separately on `codex/release-0.45.0` and `codex/release-0.46.0` for parent-first publication.
> H6–H8 remain. Latest published release remains **0.44.1**.


> **2026-10-04 — 0.46.0 candidate verified, not published.** C adds stored plan-limit parsing and uses
> existing child-plan admission. Full gate: 2,248 passed, 8 skipped; lint/format/types clean.
> Ten new cases pass on the installed wheel outside checkout; ten mutations bite. The 0.45.0 candidate
> is frozen on `codex/release-0.45.0`; candidates must land and publish parent-first, one at a time.
> The owner authorized continued preparation without waiting for publication. D and H6–H8 remain.
> Latest published release remains **0.44.1**; no protected branch or product pin changed.


> **2026-10-04 — 0.45.0 candidate verified, not published.** H11-E binds a stored procedure
> on the kit-owned model loop; unsupported pre-binding is reported as `agent.skill`, while CLI
> skill choosing remains governed and checked. PostgreSQL runtime defaults to DDL-free access.
> Full gate: 2,238 passed, 8 skipped; lint/format/types clean. All 17 new cases pass on the installed
> wheel outside the checkout; 20 mutation checks bite. Database checks used a disposable server.
> Release preparation stays on `phase-66-the-short-list`; protected landing is the owner's.
> C, D and H6–H8 remain for later separate releases. Latest published release remains **0.44.1**.


> **Decisions closed, 2026-10-04 — D190 and ecosystem initiative 0002, *generic before product*.**
> The runtime layer defines fifteen file-and-shell operations by name, in the layer whose own
> boundary rule forbids it — so D184's parity list is **what the successor should not inherit**, not
> a gap in it. D-M: those tools are a **pack** of components, never core or mandatory. D-N: **build**
> Shadow's Proposal port. D-O: the genericity test is enforceable as **D190**. D-P: an outside-world
> capability is a port plus an optional adapter. The paste-ready brief is
> [`handoffs/2026-10-04-prompt-for-the-codex-lane.md`](/handoffs/2026-10-04-prompt-for-the-codex-lane.md).
>
> **Handoff, 2026-10-03 — HDK's work moved to a Codex lane.** Start from
> [`handoffs/2026-10-03-to-the-codex-lane.md`](/handoffs/2026-10-03-to-the-codex-lane.md). **BUG-237
> is first**, released as **0.44.1** from the `v0.44.0` tag: the PostgreSQL adapters issue DDL at
> runtime, so a restricted database role cannot open them, and it blocks Intent Studio's 0.7.0. Then
> 0.45 onward **one item per release** (E, C, D, then H6–H8, each confirmed before being fixed) — a
> release train, not a batch, and the handoff names where that collides with D9's minor-per-contract
> rule. HDK is maintenance only from here, and **D189** sets its retirement. Lane P reads this file from git — keep it current, and
> put replies in `specs/epics/`.

> **Last Updated**: 2026-10-02 — **phase 65 complete on its branch: the claims are true.** Lane P's
> audit of 2026-10-02 lists forty items; its A-group is claims this kit already made and did not keep.
> Five were confirmed against the source before the phase opened, and **three originate in our own
> phases 62 and 64**: `tools_offered` narrowed nothing while two fields reported it honoured
> (BUG-230); a key-backed model discarded the mode's `model` (BUG-231); a key-backed thread forgot its
> turns with nothing saying so (BUG-232); a fixed 600s ceiling failed long turns and counted a
> person's thinking time (BUG-233); and 0.43.0's agent selection survived neither `set_mode` nor a
> resume (BUG-234). All five closed in **v0.44.0**. Wave 1 only, by the owner's decision of
> 2026-10-02 — every other audit item is named in the phase overview's *Out*, on the ground that new
> capability belongs to the native line. Suite 2058 → 2146, mypy strict 507 files. ENH-052 and TD-020 filed; **BUG-235 filed and closed
> inside the phase** — the narrowing had reached a CLI's calls and not its listing, found by
> re-reading G1 against lane P's BUG-258. Lane P's BUG-258 itself is answered: it is BUG-226/227,
> fixed in **0.34.2**, verified on this tree.
>
> Before it, **Epic 0011: v0.38.0 through v0.43.0 released and published** (both distributions, all
> seven files each, verified from outside CI). Eleven of lane P's twelve asks of 2026-10-01 shipped;
> ask 10 unscheduled with a stated reason. Two defects nobody had reported were opened and closed:
> ENH-051 (instructions never reached Codex) and BUG-229 (a key-backed model never received them *and*
> the thread reported them honoured). Latest recorded code version **v0.44.0**. **Current Phase**: 65,
> on `phase-65-the-claims-are-true`, awaiting the landing gate. Everything below predates Epic 0011
> and has not been re-audited by it.
>
> *(Historical header, from before Epic 0011:)* — **v0.34.2 released** (BUG-226/227/228 from lane P's walk of the
> installed app; tagged and on `main`, the gate run locally — GitHub Actions still refusing jobs); documentation ownership transferred; latest recorded code version
> **v0.34.2**. This repository is the maintenance-supported
> Python/LangGraph implementation and the canonical history through Phase 45. Future work starts
> with Phase 46 in the sibling [`shadow`](../../shadow/specs/status.md) repository; its
> [native architecture](../../shadow/specs/architecture/native-foundation.md) and
> [roadmap](../../shadow/specs/planning/roadmap.md) are canonical.
> Completed phases keep their IDs; old planned 34/35/37–40/42/43 are retired through the map.
> This repository, its packages and imports have **not** been renamed.
> **GitHub Actions runs again**, and **0.34.2 is published complete** — both distributions, all
> seven files. Actions refused jobs from 2026-09-19 21:23 UTC for billing; the kit's wheel and sdist
> went up from the laptop meanwhile, and the Linux helper's five could not, so 0.34.2 did not
> resolve on Linux for a few hours. The publish workflow — made re-runnable with `--check-url`, so
> the already-published two are skipped rather than failing the run — finished it on 2026-09-30
> (run `36680496191`, every job green including the helper's confinement leg and the fresh-install
> smoke). Verified from outside CI: `shadow-hdk==0.34.2` resolves on `manylinux2014` x86_64 **and**
> aarch64, pulling `shadow-hdk-linux-sandbox==0.34.2`.
> Historical copies of the future plan remain here for provenance and link continuity, but are not
> edited as the delivery source. Research and repository strategy are canonical in
> [`shadow-ecosystem`](../../shadow-ecosystem/README.md). The running implementation remains
> Python/LangGraph. Historical release/CI facts below have not been re-audited by this change.
>
> 1,846 non-live tests; mypy strict over 471 files; one distribution, `shadow-hdk`, at
> **0.34.0** (protocol 3, unchanged), and beside it the Linux helper `shadow-hdk-linux-sandbox` at the same number.
>
> **Latest Release**: **v0.34.0**, released 2026-09-20 — Phase 45 **truth both ways**: `Usage`/`Spent`
> cache tokens (D141); a typed `session_gone` on the record, raised, on the wire (D139) — with
> BUG-059/060 closed; `turn(attributes=)`/`resume(attributes=)` (D140) — with BUG-061 closed; Codex
> `model`/`effort` as data, measured; `ask` asks before a web read from the process (D138); CI on
> 3.12–3.14; the vendor-name invariant; Phase 36's proof on Claude Code. Contract additions and
> three named behaviour changes, protocol 3 unchanged — a *Pins* row. Before it **v0.33.0**, released 2026-09-20 — Epic 0010, Phase 41 **Linux confinement**:
> a confined mode opens on Linux — Ubuntu 24.04 with its default AppArmor included — through the
> kit's `shadow-hdk-linux-sandbox` helper (Landlock + seccomp applied before exec; a second
> distribution in lockstep, a dependency under a Linux marker), bubblewrap behind it, the D36 proof
> deciding which is in force and `Isolation.mechanism` naming it on the evidence; CI runs the suite
> on Linux both ways and on macOS, a red runner blocking a release. Contract additions, protocol 3
> unchanged — a *Pins* row. Before it **v0.32.1** (BUG-056) and **v0.32.0**, released 2026-09-19 — Phase 44 **tools as code, from any
> language**: `thread/start {host_components: true}` carries a host's components by inversion (D21)
> on the thread door; the TypeScript client gains `tool()`, `components.serve`, a `Transport` and a
> stdio sidecar (`shadow-hdk-client/node`); the D36 proof reads stdout (BUG-057) and the whole
> suite runs on Python 3.14. Contract additions, protocol 3 unchanged — a *Pins* row. Before it
> **v0.31.0**, released 2026-09-18 — Epic 0009, Phase 36 **plan admission**:
> a plan is a composition admitted whole — shape, existence and effects — under limits that narrow
> host → mode → parent, before its first step runs; `plan_admitted`/`plan_refused` on the record;
> `compose` a registered component, so a resident CLI plans through the socket (proven live on
> Codex); plan limits live on the mode; a plan may run after its planner; `thread/amend` for a
> parked plan; `unmapped_behaviour` named rather than dropped (ENH-020). Contract additions
> (protocol 3 unchanged), so a *Pins* row. BUG-054 and BUG-055 closed. Before it **v0.30.0**, released 2026-09-15 — Epic 0008: evidence-backed
> capability selection, one durable model/CLI agent surface, and current-authority append-only
> irreversible effects. GitHub Actions published to PyPI and passed the fresh-install smoke. Before
> it **v0.29.1**, released 2026-09-14 — BUG-044 closed: `ask_person` answered `park` is kept, not answered `Parked()`; found by the React example wiring D88 to an input card. Before it **v0.29.0** — Phase 30, a product owns what it owns
> (D87–D94): `Conversation`, `Parked` and `turn(on_question="park")`, the agent streams, tokens
> on `Spent`, `shadow_hdk.testing`, `Questions`, `Routed`, typed refusals, `RunStore`,
> `ThreadRecord.version`, `idle_seconds`, a stream that reattaches. Contract change (additions;
> `RunOptions.approvals` typed on the port), so a *Pins* row. Before it **v0.28.0**, released 2026-09-14 — Phase 29, one app server behind every
> surface (D79–D86): `[store] url` (sqlite | Postgres, the `[postgres]` extra), a parked turn
> resumed after a restart, a thread's hold, `principal`/`attributes` and `scope`, batteries as
> rows, `budget`/`spent` on the record, `ask` and `deny` rules in every mode, `/healthz` and
> `admin/*`. Contract change (new parameters and methods; the `ThreadStore` port grew), so a
> *Pins* row. Before it **v0.27.2**, released 2026-09-13 — the React example's approval cards:
> a call the mode asks about is one item, named and kept across its park (BUG-040). Before it
> **v0.27.1** — the example's first connect: the SSE stream opens with a frame (BUG-038), the
> TypeScript client runs in a browser and is a package (BUG-039). Before it **v0.27.0** — one distribution with extras (D78);
> BUG-036, BUG-037; mypy over the whole tree; the sdist declared; published to PyPI. Before it
> **v0.26.1** (the URLs and classifiers; the publish workflow, tagged but never released — it
> would have published eighteen names). Before it **v0.26.0** — the packages
> proven as published artefacts (BUG-035, the wheel invariant, the clean-venv proof). Before it v0.25.3 (BUG-034; the
> specs synced), v0.25.2 (D77 — `start_held`,
> `LineBuffer`, the root-name rule), v0.25.1 (a battery's process
> held, BUG-033; Claude Code from a clean scope, ENH-012) and **v0.25.0** — Phase 28, the workspace (D73–D76).
> Contract change (roots, `WorkspaceChanged`, `tools/list`, `skills/list`, `thread/add_root`,
> `AgentPort.open(resume=)`, the `ask` mode, a child's context), so a *Pins* row. Before it
> v0.24.0 (Phase 27, batteries and the facade, D70–D72), v0.23.0 (Phase 26, any language, D67–D69), v0.22.0
> (Phase 25, the host's controls, D61–D66), v0.21.0 (the words, mid-phase), v0.20.0 (the studio inline; seven bugs found by using it, D59,
> D60), v0.19.0 (hardening to Phase 24: D57 park, D58 live, `Questions`, Codex measured), v0.18.0 (Phase 24, the skill registry), v0.17.0 (Phase 23, a host —
> the consumable line), v0.16.0, v0.15.0, v0.14.0, v0.13.1. All MIT
> **Health**: On Track

## Summary

Shadow is a generic framework for building and running agents, workflows and custom harnesses.
The current `shadow-hdk` distribution executes with Python/LangGraph and a Rust Linux helper.
The target is one Rust execution foundation with progressive controls, SDKs and optional component
ecosystems; no product owns its vocabulary or policy. The port set is open. Native behavior,
distribution, binding and resource claims must pass Epic 0010's proof and migration gates before
the new engine becomes the default. Documentation approval has not started Phase 46.

## Completed Phases

> Every phase is merged and released. `main`, `staging` and the phase branches met at
> `c0bc9e7` on 2026-09-10; each phase carries a `phase/NN-*` tag, and the release column is
> the version that first shipped it. Several phases share a version because a version is a
> **contract** change (D9), not a phase boundary.

| Phase | Name | Status | Released |
|-------|------|--------|---------|
| 0 | The runtime, and the bare test goes green | Complete, merged | **v0.1.0** |
| 1 | Real adapters, streaming, modes | Complete, merged | **v0.2.0** |
| 2 | The spike — J1 | Complete, merged | **v0.2.0** |
| 3 | The workspace, and code | Complete, merged | **v0.2.0** |
| 4 | The ACP bridge | Complete, merged | **v0.2.0** |
| 5 | Checkpoints, and a parked run survives | Complete, merged | **v0.3.0** |
| 6 | The compiler completed | Complete, merged | **v0.4.0** |
| 7 | Sub-agents | Complete, merged | **v0.5.0** |
| 8 | Patterns, skills, replay, compaction | Complete, merged | **v0.5.0** |
| 9 | The wire | Complete, merged | **v0.6.0** |
| 10 | Effect rules | Complete, merged | **v0.6.0** |
| 11 | Contained sandboxes | Complete, merged | **v0.6.0** |
| 12 | Derivation | Complete, merged | **v0.6.0** |
| 13 | Leases on effects, driver supply chain | Complete, merged | **v0.7.0** |
| 14 | Telemetry | Complete, merged | **v0.7.0** |
| 15 | The environment contract | Complete, merged | **v0.8.0** |
| 16 | MQTT | Complete, merged | **v0.8.0** |
| 17 | The audit — every P0 | Complete, merged | **v0.10.0** |
| 18 | The P1s | Complete, merged | **v0.12.0** |
| 19 | The P2s, and the documents | Complete, merged | **v0.13.0** |
| 20 | Providers — your key, or your subscription | Complete, merged | **v0.14.0** |
| 21 | The visible agent | Complete, merged | **v0.15.0** |
| 22 | The environment | Complete, merged | **v0.16.0** |
| 23 | A host, in-process and in any language | Complete, merged | **v0.17.0** |
| 24 | The skill registry | Complete, merged | **v0.18.0** |
| 25 | The host's controls | Complete, merged | **v0.22.0** |
| 26 | Any language | Complete, merged | **v0.23.0** |
| 27 | Batteries and the facade | Complete, merged | **v0.24.0** |
| 28 | The workspace | Complete, merged | **v0.25.0** |
| — | the packages as published artefacts; published to PyPI | Complete, merged | **v0.26.0**, **v0.26.1** |
| — | one distribution with extras (D78); the React example's finds | Complete, merged | **v0.27.0**, **v0.27.1**, **v0.27.2** |
| 29 | One app server behind every surface | Complete, merged | **v0.28.0** |
| 30 | A product owns what it owns | Complete, merged | **v0.29.0** |
| 31 | A host knows what it can trust | Complete, merged | **v0.30.0** |
| 32 | One agent surface | Complete, merged | **v0.30.0** |
| 33 | Authority at the act | Complete, merged | **v0.30.0** |
| 36 | Plan admission (Epic 0009) | Complete, merged | **v0.31.0** |
| 44 | Tools as code, from any language | Complete, merged | **v0.32.0** |
| 41 | Linux confinement (Epic 0010) | Complete, merged | **v0.33.0** |
| 45 | Truth both ways | Complete, merged | **v0.34.0** |

## Ad-hoc / Patch Releases

| Version | Date | Type | Summary |
|---------|------|------|---------|
| v0.44.1 | 2026-10-03 | quick-task | BUG-237 — a restricted database role can open the PostgreSQL adapters. They executed their table DDL when a pool first opened **and again after every `aclose()`**, so a production runtime role with no DDL rights failed with SQLSTATE 42501 and the application could not start; reported as Intent Studio's BUG-280, blocking their 0.7.0. Provisioning the tables in advance did not help, and that decides the fix: `CREATE TABLE IF NOT EXISTS` is **not** DDL-free, because PostgreSQL checks the CREATE privilege before the existence check — held against a real server by a test, since it is counter-intuitive enough to measure rather than assert. So the schema is no longer executed at runtime. `prepare(url)` and a `shadow-hdk-prepare` console script create every table and call LangGraph's own `setup()` under an owner role, idempotently, recording the version in a new one-row `shadow_hdk_schema_version` table — without which *migrates* has nothing to migrate from and *behind* nothing to compare against. `prepared=True` issues no DDL and verifies with one catalogue query, failing `SchemaNotPrepared` or `SchemaBehind` named at startup. `runtime_grants(role)` publishes the restricted role's grants as data, SELECT only on the version table, and the test grants exactly what it publishes. **Opt-in here** so a patch inverts nothing; the default flips in the first 0.45 release as a named behaviour change. Verified under two real roles — prepare as an owner, then every adapter's open, **reopen** and ordinary operations as a role that cannot create tables — and CI now runs that test. A patch with an additive published surface, so a *Pins* row (D9); protocol 3 unchanged. |
| v0.36.0 | 2026-09-30 | ENH-042, ENH-048 | A change names a region: `edit_file(path, edits[])` replaces regions in order, all of them or none, refusing an `old` that is absent or that appears more than once — before anything is written, so a failed edit leaves the file that was there; `move_file(from, to)` refuses a destination that exists, which is what keeps a move honestly `write`-class. No kernel change and no new record machinery: both derive as `write`, and the diff is the call's own inputs, already on the record and the approval card. Designed through `/brainstorm-phase`, carried as a quick-task because phases 46–58 belong to `shadow`. Contract additions — a minor (D9), a *Pins* row; protocol 3 unchanged. |
| v0.35.0 | 2026-09-30 | ENH-041 | The read-class file tools: `glob` (`**` crossing separators, `*` not), `grep` (a regular expression over contents, each match with path and 1-based line, optionally narrowed by a glob), and `read_file(offset, limit)` in lines. All three derive from `list`/`read`, so their profiles carry no writes and the shipped `ask` mode does not stop a person for a search — the point of them, since every search was previously a `run_shell` that `ask` rightly did stop. Built on `_list`/`_read` in the base, so every environment gains them and no adapter implements anything. Caps announced rather than silent; a range past the end refused naming the line count; `read_file` without a range unchanged. Lane P's first pick from the desktop walk. Contract additions in the published shape — a minor (D9), a *Pins* row; protocol 3 unchanged. |
| v0.34.2 | 2026-09-30 | quick-task | BUG-226 — an address is a command, never a command line: nothing splits `ToolSource.address` on any transport, so a kit installed inside an application bundle (`/Applications/Intent Studio.app/…`) hands its CLI a relay that starts, where before the CLI was launched as `/Applications/Intent` and ran with no tools at all; the relay is resolved beside the running interpreter before `PATH`. BUG-227 — the ACP transport carries the registry's port and token to the relay it launches, which it had been dropping (`env=[]`), so a governed OpenCode had no tools for a second, independent reason. BUG-228 — a parked call is reported as a fact about the call, not an instruction a model can read back to the person, and a parked turn's own text is no longer that agent-facing note. All three measured by lane P on an installed 0.6.10; a kit-only reproduction for the first. No contract change. |
| v0.34.1 | 2026-09-20 | quick-task | BUG-062 — a fork is a fresh provider session seeded with the transcript (D139's move after `session_gone` works; `rollback`'s `seeded_turns` is finally true); BUG-063 — a thread turn's cache tokens reach `Spent` (the step→meter join and `settle` carry them). Both measured by lane P on 0.34.0 with kit-only reproductions. No contract change. |
| v0.32.1 | 2026-09-19 | quick-task | BUG-056 — a change that reopens the provider is refused during a turn, typed (`turn_running`); the turn lock held across the change |
| v0.25.3 | 2026-09-13 | patch | BUG-034 the mode in `harness.toml`/`--mode`/`Harness(mode=)` is a mode id (`ask` included), refused by name at open; `requires` refuses an unknown environment name; the architecture specs synced to the tree |
| v0.25.2 | 2026-09-12 | patch | D77 one rule, one implementation: `start_held` the one place a session leader is started (an invariant refuses the next copy); `LineBuffer` the one framing; a root's name a rule, not an `exists()` guess |
| v0.25.1 | 2026-09-12 | patch | BUG-033 a battery's MCP server is a held session leader, ended with its group; ENH-012 Claude Code launched with no settings sources and no auto-memory — a run's instructions are the mode's behaviour only |
| v0.25.0 | 2026-09-12 | phase 28 | the workspace: one or many roots per thread, added live; the environment and the provider follow the mode; the `ask` mode; the registries visible; a child judged in its parent's context (D73–D76) |
| v0.24.0 | 2026-09-12 | phase 27 | batteries and the facade: a battery is a file (wigolo, ddgs), `Harness.load` and `harness.toml`, `budget`, the optimiser specified (D70–D72) |
| v0.23.0 | 2026-09-12 | phase 26 | any language: the thread, the handles and the store over the wire; `shadow-hdk serve`; the TypeScript client; the studio on the wire (D67–D69) |
| v0.22.0 | 2026-09-12 | phase 25 | the host's controls: Thread/Turn/Item/Activity, modes = policy + behaviour, rules and input, the Store (D61–D66) |
| v0.21.0 | 2026-09-12 | phase 25 (mid) | the record speaks the industry's words (D61) |
| v0.20.0 | 2026-09-12 | hardening | the studio inline; five scenarios; BUG-023–029 closed (D59, D60) |
| v0.19.0 | 2026-09-12 | hardening | BUG-020/021/022 closed (D57, D58); Codex measured; the studio |

## Active Phase

| Phase | Branch | Status | Progress |
|-------|--------|--------|----------|
| 64 — an agent is data (Epic 0011) | `phase-64-an-agent-is-data` | released as v0.43.0 | 5/5 groups |
| 65 — the claims are true | `phase-65-the-claims-are-true` | released as v0.44.0 | 6/6 groups |
| 66 — the short list | `phase-66-the-short-list` | 0.47.0 verified, owner landing pending | G1–G5 done; G6 remains; release checkpoints in G7 |

> None. Epic 0011's phases 59–63 are all landed on `main` and released — see the checkpoints below.

## Epic Release Checkpoints

| Phase | Branch | Evidence | Release |
|-------|--------|----------|---------|
| 59 — a change on the record (Epic 0011) | `phase-59-a-change-on-the-record` | ruff clean, format 542 files, mypy strict 483 files, 1936 passed / 20 skipped; sixteen mutations biting; ENH-051 measured live on claude-code 2.1.284 with `--system-prompt` removed from its record, and the Codex leg **unmeasured** because a ChatGPT-account codex refused every model tried | **v0.38.0** released |
| 60 — the write-class completes (Epic 0011) | `phase-60-the-write-class-completes` | ruff clean, format 545 files, mypy strict 485 files, 1957 passed / 20 skipped; eleven mutations biting, two of which found that the background path's sandbox wrap and narrow environment were untested claims in a docstring | **v0.39.0** released |
| 61 — undo and an agent's own workspace (Epic 0011) | `phase-61-undo-and-an-agents-own-workspace` | ruff clean, format 551 files, mypy strict 490 files, 1986 passed / 20 skipped; eighteen mutations biting, two needing their assertion tightened before they would | **v0.40.0** released |
| 62 — what a run carries (Epic 0011) | `phase-62-what-a-run-carries` | ruff clean, format 556 files, mypy strict 494 files, 2011 passed / 20 skipped; nineteen mutations biting; the ENH-012 sentinel re-measured on claude-code 2.1.284 both ways. **The first v0.41.0 tag went red on every CI job** — a retrospective named a migration note absent from its own tree — and was corrected before release, nothing having been published | **v0.41.0** released |
| 63 — visible and steerable (Epic 0011) | `phase-63-visible-and-steerable` | ruff clean, format 559 files, mypy strict 496 files, 2021 passed / 20 skipped; six mutations biting, one finding a refusal tested at the wrong layer; CI green on all 13 jobs at `ad79948` | **v0.42.0** released |
| 31 — a host knows what it can trust | `phase-31-a-host-knows-what-it-can-trust` | incorporated in combined 1,688-pass v0.30.0 gate | v0.30.0 released |
| 32 — one agent surface | `phase-32-one-agent-surface` | incorporated in combined 1,688-pass v0.30.0 gate | v0.30.0 released |
| 33 — authority at the act | `phase-33-authority-at-the-act` | combined gate, artifacts, schemas and client green | v0.30.0 released |
| 36 — plan admission (Epic 0009) | `phase-36-plan-admission` | 1,773 non-live passed, mypy 452 files, ruff clean, OKF conformant, schemas without drift, the TypeScript client generated and built, the 0.31.0 wheel installed fresh and answering `initialize`; live on Codex CLI 0.154.0 | v0.31.0 released |
| 44 — tools as code, from any language | `phase-44-tools-as-code` | 1,784 non-live passed on 3.12 **and** on 3.14; mypy 457 files; ruff clean; OKF conformant; schemas without drift; the TypeScript client generated and built; the 0.32.0 wheel installed fresh and answering `initialize`; the TS host tool called back over HTTP and stdio | v0.32.0 released |
| 41 — Linux confinement (Epic 0010) | `phase-41-linux-confinement` | 1,799 non-live passed on 3.12 **and** on 3.14 (macOS); on CI: 1,818 on Linux with Landlock in force, 1,799 on Linux with bubblewrap, 1,799 on macOS; the crate's 12 confinement tests on the ubuntu-24.04 runner; four platform wheels built, the x86_64 one installed and watched confining; mypy 461 files; ruff clean; OKF conformant; the 0.33.0 wheel installed fresh and answering `initialize` | v0.33.0 released |
| 45 — truth both ways | `phase-45-truth-both-ways` | 1,846 passed on 3.14 **and** on 3.12; mypy 471 files; ruff clean; the TS types without drift; OKF conformant; CI green on `aca389d` (the same code; the release commit's run refused by GitHub billing); live: Phase 36's proof on Claude Code, Codex `-m`/`-c model_reasoning_effort`, cache tokens and `session_gone` on both CLIs | v0.34.0 released |

## Transferred Roadmap — Canonical in Shadow

> These identities are retained for provenance. Their canonical overviews, dependencies and
> eventual plans/tasks live in [`shadow`](../../shadow/specs/planning/roadmap.md); do not start or
> update them in this repository.

| Phase | Depends on | Makes true |
|------|------------|------------|
| 46 — architecture proof | 45 | evidence-backed behavior baseline, recovery slice, reuse/binding decisions and resource budgets |
| 47 — native Core and runtime | 46 | shared Rust execution, authority and durable recovery |
| 48 — components and strategies | 47 | native usefulness, optional hosts and agent/workflow/hybrid strategies |
| 49 — SDKs and embedding | 48 | Rust/Python embedding; Python/TypeScript authoring and managed/remote clients |
| 50 — Windows lifecycle | 47 | native process ownership and honest supported/refused capabilities |
| 51 — native distribution | 49, 50 | pinned platform artifacts, SDK packaging and install/run evidence |
| 52 — native migration | 51 | compatibility, persisted-data handling, rollback and native acceptance |
| 53 — harness as data | 52, 36 | parameterized composable harness definitions and bundles |
| 54 — durable run request | 53 | idempotent requests, scheduling and trigger adapters |
| 55 — context engineering | 54 | context/memory capability after the foundation and reuse work |
| 56 — UI plane | 54 | activity and generative-UI adapters, not full applications |
| 57 — collaboration | 54 | peer discovery and remote delegation |
| 58 — evaluation and evolution | 55 | fixed evaluators and human-approved improvement rollout |

## Blockers

| ID | Description | Severity |
|----|-------------|----------|
| _(none)_ | | |

## Critical Items (P0)

| ID | Type | Description |
|----|------|-------------|
| _(none)_ | | The audit's P0s (BUG-004–007, TD-009) closed in Phases 17–18; open now: ENH-005–008 (P2–P3) — see the backlog |

## Next Actions

**Current action:** use this repository only for urgent, generic maintenance of the released
Python/LangGraph line. Start native Phase 46 only from the canonical `shadow` specifications after
its ordinary brainstorm/start gates. The numbered list below is the prior release-operations
handoff (2026-09-20), retained for audit; its external CI/billing state needs a fresh check before
use.

1. **GitHub billing** — fix it, then `gh run rerun 35470259560` (CI on the release commit) and the `v0.34.0` GitHub release (it triggers the publish workflow: the kit and the helper's wheels, PyPI, the smoke). Until then the tag can stand and `uv publish` from the laptop with the owner's token is the fallback
2. ENH-021 after the publish: the React demo re-pinned to 0.31.0 with a chapter from the live run — a plan refused with its reasons, a plan approved as one card, the CLI planning through the socket
3. The owner's confirmations owed: Epic 0009's two amendments (D108/D121 name a step's asks and refusals rather than pre-empting them; ENH-020 folded into Phase 36, shipped in G6); the Claude Code half of the live measurement (signed out here); the ecosystem board's H36 row, Pins and Log
4. Phase 45 — the rest of what the product asked for, generic (BUG-056 shipped in 0.32.1): ENH-023 (cache tokens on `Usage`), ENH-024 (a typed `session_gone`), ENH-028 (Codex `model`/`effort` measured), ENH-032 (3.12/3.13/3.14 in the matrix; its blocker BUG-057 is closed). Claude Code is signed in again, so the owed half of Phase 36's live proof can run there too
5. The ecosystem board's Pins rows for 0.30.0 → 0.33.0 (`intent-ecosystem/lanes/board.md`, lane P's repository — the text is in the kit's handover) and ENH-037/038/039 answered back to lane P
6. Still conditional: a Linux host for the remaining containment proofs, and a lawyer's read on AGPL at arm's length. The Codex relay proof landed in Phase 36 G3

## Key Decisions Made

- D1–D13 in `specs/architecture/decisions.md`, settled at founding from `09` and the founding conversation; recorded on Epic 0001
- D14–D22 settled per phase: D15 cancellation (6), D16 held children (7), D17 files and D18 compaction (8), D19 state-as-JSON, D20 `Spent`, D21 the crossed context (9). **D22 — the port set is open**: six is a count, not a constraint, settled by the owner 2026-09-10, which closes O4
- **D95–D106** are settled once in Epic 0008: one Shadow/two surfaces; typed capability-requirement evidence; provider/environment/authority separation; one agent surface; approval separate from authorization; revisioned act-time authority; crash-safe effect transactions, grants, uncertainty and journal; product ownership; standards at adapters
- **Licensed MIT** 2026-09-10 (O3), declared in every package and verified in the built wheels
- The name and the repository: `10-the-roadmap.md` §7d; the two-lane plan: §3b; the board: `intent-ecosystem/lanes/board.md`

## Recent Changes

- 2026-09-10 — **Phase 9 begins**: what crosses a boundary is settled before anything is built on it. A checkpoint *is* a wire, so the graph's state holds JSON rather than our classes — which closes TD-001 while it was still green — and `Spent` says what a step cost instead of leaving it in an output dict by convention
- 2026-09-10 — **Phase 8 complete**: patterns and skills are files a team writes, a big catalogue is names until the model asks, a run replays for nothing, and a model can summarise itself and keep a helper. Building the helper verbs found a Phase 7 bug — a held child was woken on the ceiling it started with, which a parent that had spent since could no longer afford
- 2026-09-10 — **Phase 7 complete**: a child can be kept between messages, and it is a checkpoint rather than an object left running. Building it found that `Await` had never parked — the architecture said `interrupt()` since Phase 0 and the compiler treated it like `Invoke`, so half the grammar's waiting was a type nothing exercised
- 2026-09-10 — **Phase 6 complete**: the compiler says *where*. A nested composite is a subgraph with its own checkpoint namespace, a host can stop a run and the record carries the words of whoever asked, and a parked run resumes from a file after the saver that wrote it is gone. Two steps sharing an id used to loop until the lease was spent; now the run ends and names the id
- 2026-09-10 — **Phase 5 complete**: a child agent uses the parent's registry through an MCP server, and what it did is on the parent's record because it was routed. The MCP topology is inverted — the parent spawns the child and serves over its pipes, because this server holds a live run and cannot be launched fresh
- 2026-09-10 — **Phase 4 complete**: another agent driven as a governed component. A mode written for the harness governs somebody else's agent without knowing it exists
- 2026-09-10 — **Phase 3 complete**: the agent can make things — a workspace it cannot write outside of, and a sandbox that says honestly what it is not. What the deployment is decides what the model can see
- 2026-09-10 — **Phase 2 complete**: J1 answered. ACP reports usage and sometimes a price; a turn always ends with a stop reason; there are two distinct ways to refuse; and nothing stops an agent looping on a denial, so a driver needs its own clock — which the lease already is
- 2026-09-10 — **Phase 1 complete**: one model adapter over every LangChain provider, proven live against HuggingFace; MCP components with effects derived from annotations; modes as data; the harness on real everything
- 2026-09-10 — **Phase 0 complete**: the runtime, the agent as a component, the basic adapters, the bare harness green with zero product code
- 2026-09-10 — founded: charter, principles, success criteria, roadmap, architecture, Epic 0001, Phase 0
- 2026-09-10 — momentum installed; joined `intent-ecosystem` as member `shadow-hdk`
- 2026-09-10 — the kernel, two invariants and the strict-xfail bare-harness test (`16eb1fd`, `4047434`)
