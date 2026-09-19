---
type: Epic
id: "0010"
slug: cross-platform
status: planned
owner: avinash-singh-io
started: "2026-09-19T11:53:47.163Z"
phases: [phase-41-linux-confinement, phase-42-the-artifact, phase-43-windows]
policy_release: per-phase
policy_push: per-phase
policy_tdd: strict
---

# Epic 0010 — cross-platform

## Objective

The kit installs and runs on macOS, Windows and Linux as one downloadable artifact per OS with no prerequisite; process supervision and confinement are native per OS behind one contract with the D36 proof; the Python engine and the whole Python ecosystem stay exactly as they are; the engine's language (B) is a dated, evidence-based decision reviewed at the close of Epic 0009.

## Decisions

> Settled once; never re-asked. Per-phase specs are derived from this table.

| # | Decision | Rationale |
|---|---|---|
| D122 | **Layers decide separately.** The OS layer is native per OS; the ecosystem stays Python; the engine's language is a separate, dated decision (D129) | the requirements decide the first two today (three OSes, one artifact, keep the ecosystem); the third has no firing requirement and deserves evidence, not a feeling |
| D123 | **The OS layer's native parts are small static helper executables from one Rust crate, `shadow-hdk-sandbox`, one per OS, invoked by the Python leash as it invokes `sandbox-exec` today.** Detection, the profile per mode, the leash's policy and the D36 proof stay in Python; PyO3 is not required. Rust for the `landlock` and `windows-rs` crates and static binaries | grounding 2026-09-19: macOS needs no helper (`sandbox-exec` is Apple's); Linux needs one because Landlock and seccomp are syscalls the child makes on itself before `exec` (Codex ships `codex-linux-sandbox`); Windows confinement needs an elevated executable with its own manifest, which the Python process cannot be. Helpers ship inside the artifact — no wheel per Python × OS × arch — and are reusable unchanged by a native engine (B) or a TypeScript sidecar |
| D124 | **One contract, native primitives.** The leash and the sandbox keep their Python-facing contract (`Environment`, `Isolation`, `run_leashed`); each OS implements it with its own primitives — POSIX process groups · Windows Job Objects; seatbelt · Landlock+seccomp (bwrap fallback) · restricted tokens — never "POSIX and hope" | today's leash is `killpg`/`setsid`/`setrlimit` and today's Windows is silence; the same contract on three OSes is what lets the suites be the same |
| D125 | **Proof before claim, per OS** (D36 generalised). Every confinement is watched denying and allowing before a confined mode opens; where no proof exists yet on an OS, the mode refuses with `CannotEnforce` — never a silent `full`. This is stricter than Claude Code's default (warn and run unsandboxed) and equal to its `failIfUnavailable`; continuing is a mode a product chooses, never a fallback | no field runtime proves its sandbox before trusting it — the proof is the kit's one genuine addition, and it is mechanism-independent, so every swap below it is safe |
| D126 | **Same semantics on three OSes, proven by the same suites on three CI runners; a red runner blocks the release** | a green suite on one OS proves nothing about the other two |
| D127 | **One artifact per OS/arch, no prerequisite, built with PyApp fully embedded** — the interpreter and the kit inside, no first-run fetch — for macOS arm64/x86_64, Linux x86_64/arm64, Windows x86_64; the server as a container image; size and time-to-first-turn measured and recorded per OS per release, calibrated against the field's norm (Claude Code's native binary is ~100 MB, a Bun runtime inside); PyOxidizer excluded (unmaintained since 2024) | the user downloads one thing; the field ships a runtime inside a per-platform binary and nobody declines it for size |
| D128 | **The engine and the ecosystem are unchanged by this epic.** LangGraph stays; no engine code moves to Rust here; `Harness`, `Thread` and `run()` keep their signatures | this epic buys three operating systems, not a rewrite |
| D129 | **B (a native engine) is a dated decision** — at the release that closes Epic 0009, no later than 2026-12-31 — on three criteria: the LangGraph ledger (`specs/research/2026-09-19-the-langgraph-ledger.md`, BUG-055 entry one), the artifact's size and start time per OS from Phase 42, and Windows proof status from Phase 43. No native engine work starts before that review | a rewrite should be decided by a ledger and two measurements, not by a doubt; the layers make waiting free |
| D130 | **The record is the source of truth; a checkpoint is a view.** New durability work (Phase 37) builds on the kit's `RunStore` port, never on LangGraph's checkpoint classes directly | keeps the engine seam thin, so B stays cheap if it is chosen |
| D131 | **Release keys stay outside the tree.** The pipeline produces signable artifacts and verifies signatures where the OS requires; on macOS every nested Mach-O is signed with hardened runtime and Python's *allow unsigned executable memory* entitlement; certificates are the owner's secrets | the existing credentials rule, applied to Gatekeeper and SmartScreen; notarization rejects an unsigned nested binary |
| D132 | **Development on Python 3.14; consumers keep `requires-python >= 3.12`; the artifact pins the interpreter the CI matrix proves** | ENH-032 as a standing rule; the tree resolves on 3.14 with every extra; BUG-057 is the one fix the upgrade needs |
| D133 | **Linux confinement is Landlock + seccomp applied in-process by the helper, bubblewrap as the fallback, the proof deciding which is in force on this machine.** The `landlock` crate probes the kernel for the highest ABI (v4 adds TCP `bind`/`connect` control) | today the kit is bwrap-only, which Ubuntu 24.04's default AppArmor breaks; Codex's order (Landlock first, bwrap fallback) is the field's and survives that default |
| D134 | **Windows ships in two steps.** Phase 42's artifact carries process control (Job Objects) and honest `full`; confinement lands in Phase 43 by one of two models decided there with evidence — Codex's elevated model (one-time UAC, dedicated sandbox users, ACLs, firewall rules) or WSL2 as the confined path. No unelevated ACL prototype | the field mapped this fork: Codex abandoned the unelevated design (ACL stamping too slow, no network isolation without elevation) and Claude Code offers WSL2 only; there is no third model to invent |
| D135 | **Consume the OS primitives, own the proof.** `landlock`, a Job-Object crate, `windows-rs` and PyApp are consumed; SBPL generation, the profile per mode, the leash's policy and the D36 proof stay ours | principle 5 — build the loop, consume the rest; the proof is what no field runtime has |
| D136 | **`sandbox-exec`'s deprecation is an accepted, detected risk** shared with every field runtime (Codex, Claude Code and Anthropic's sandbox-runtime all use it; Apple offers no CLI replacement); the proof fails closed the day it goes, so it can never fail silent | a deprecated dependency with a detector is a known cost; one without is a latent lie |
| D137 | **Named seams left for later, not this epic's work:** network egress through a host-side proxy with an allowlist (the field's shape — Claude Code and sandbox-runtime route and mask credentials through it; Codex uses firewall rules and seccomp); cloud confinement as a microVM backend (`OpenSandbox`-class — Firecracker boots in ~125 ms; "a container is not a sandbox"). The OS layer leaves the hook for both | both are where the field is ahead of the kit; naming them keeps this epic honest about what it does not close |

## Phases and dependencies

| phase | contributes | deps |
|---|---|---|
| **41 — Linux confinement** | the `shadow-hdk-sandbox` crate opened with its Linux helper (Landlock + seccomp applied in-process, exec'd like `sandbox-exec`), shipped as the `shadow-hdk-linux-sandbox` distribution the kit depends on where Linux is the platform; `adapters/environment/local.py` choosing among the machine's mechanisms in the field's order — the helper, then bubblewrap — with the D36 proof deciding which is in force and the evidence naming it; the leash unchanged (POSIX on both); CI proving Linux confinement on Ubuntu 24.04 with its default AppArmor (the helper) and with the helper set aside (bubblewrap, the sysctl), plus a macOS runner — the full Python suite green on both, a red runner blocking a release | — |
| **42 — the artifact** | *optional, when a sidecar without a first-run network fetch is required (amendment 2026-09-19):* one download per OS/arch (PyApp, embedded), `shadow-hdk` as the entry, the helpers inside; the signing pipeline (Developer ID + notarization; SmartScreen); the fresh-install smoke **from the artifact** every release; size and time-to-first-turn recorded; the `serve` container image | 41 |
| **43 — Windows** | *deferred until the owner asks (amendment 2026-09-19); WSL2 meanwhile:* the leash's Windows primitives (Job Objects) so the suite runs on a Windows runner with confined modes refusing honestly, then confinement by the model D134 decides with evidence, behind the D36 proof: `workspace-write` and `read-only` open on Windows with `proven=True`; the elevated helper pair if that model wins | 41 |

Order is computed from deps: 41 first; 42 and 43 may run as parallel lanes, each when it is asked for.

## Non-goals

- A native engine or scheduler (B) — reviewed under D129, not built here
- Windows confinement as a *precondition* for the Windows artifact — Windows ships with honest `full` first if 43 lands after 42 (D134)
- Network egress control through a proxy, and credential masking — a named seam (D137) for Phase 35/38
- Cloud confinement — a microVM backend, not the OS layer (D137)
- An auto-update mechanism (the installer's, the product's or the OS's)
- Mobile operating systems
- Phase 34's bundling of *harnesses* (Epic 0009) — it builds on 42's launcher; it does not replace it
- The wire-seam work ENH-030 / ENH-031 (Epic 0009, D119)

## Completion criteria

> Checkable. "It works" is not a criterion.

1. The `shadow-hdk-sandbox` crate's tests and the OS layer's contract suite pass on macOS, Linux and Windows CI runners; a red runner blocks a release.
2. `runtime/leash.py` and `runtime/processes.py` delegate per OS through one contract; the full Python suite passes on all three runners.
3. The Linux proof passes on Ubuntu 24.04 with default AppArmor (Landlock path) and on a kernel without Landlock (bwrap fallback), each saying which is in force.
4. On a fresh machine of each OS: download one artifact, run `shadow-hdk serve harness.toml --stdio`, answer `initialize`, complete one turn with a scripted provider — the smoke **from the artifact**, every release.
5. The macOS artifact notarizes; the Windows artifact passes SmartScreen with the owner's certificate; the Linux artifact runs on a clean image.
6. Artifact size and time-to-first-turn recorded per OS per release, within Phase 42's targets or the deviation recorded.
7. On the Windows runner, a write outside the roots is watched denied, the network denied, a write inside allowed — `workspace-write` opens with `proven=True` (Phase 43), and the model chosen is recorded as a decision with the evidence.
8. The LangGraph ledger exists under `specs/research/`; the B review is recorded as a decision — started, deferred or declined — with the three criteria's values (D129).
9. No engine code in Rust; the three facade signatures unchanged; the Python suite's count does not drop.
10. The `serve` container image published and smoke-tested per release.

## Amendments

> Operator changes made during the run land here, newest last, and become
> inputs to the derivation of every not-yet-started phase.

- 2026-09-19 (the owner's order, after `research/2026-09-19-how-the-field-ships.md`) — **The order is Linux confinement first; the artifact optional; Windows deferred.** The product's laptop release is macOS + Linux with the kit in-process, so the blockers are BUG-056 (shipped in 0.32.1) and Linux confinement on Ubuntu 24.04. Phase 42 is re-scoped: its Linux half (the Landlock helper with bwrap fallback; CI proving Linux confinement) comes first as the next lane; the per-OS artifact (PyApp, signing, the smoke) follows only when a sidecar without a first-run network fetch is required — a host may ship `uv` and run the kit through it meanwhile (mechanism C3). Phases 41 and 43 (Windows runs; Windows confined) are deferred until the owner asks; WSL2 is the Windows path meanwhile. D122–D137 unchanged.
- 2026-09-19 (membership, before the first lane opened) — **The phase list is re-cut to match the order above.** The Linux helper had sat in "41 — the OS layer" beside Windows process control; the amendment above named "Phase 42's Linux half", which was loose. The membership is now: **`phase-41-linux-confinement`** (the next lane — the helper, the fallback, the proof deciding, CI on Ubuntu 24.04 and macOS); **`phase-42-the-artifact`** (optional, deps 41); **`phase-43-windows`** (deferred, deps 41 — runs first, then confined, absorbing the old 41's Job Objects). Completion criteria 1–3 and 9 are what Phase 41 makes true on Linux and macOS; 4–7 and 10 wait on the phases that own them. One consequence for D123: with the artifact optional, the Linux helper reaches a machine the way the kit does — as a distribution, `shadow-hdk-linux-sandbox`, one platform wheel per OS × arch tagged `py3-none` (no wheel per Python version, which is what D123 declined), a dependency of `shadow-hdk` under a Linux marker; the artifact, when it comes, carries the same binary inside. D122–D137 otherwise unchanged.
- 2026-09-19 (Phase 41 at its gate) — **Criteria 1–3 and 9 on Linux and macOS.** (1) the crate's tests and the environment's contract suite pass on the Linux and macOS runners, four CI jobs plus the wheel matrix, a red one blocking a release; (2) the leash is unchanged and one contract holds on both — Windows waits on 43; (3) the Linux proof passes on Ubuntu 24.04 with its default AppArmor through the helper (`mechanism == "landlock"`) and, the helper set aside, through bubblewrap with the sysctl (`mechanism == "bubblewrap"`), each saying which is in force — proven on the same runner image rather than on two kernels, since no hosted runner lacks Landlock; (9) no engine code in Rust, the three facade signatures unchanged, the suite's count up (1,799 non-live on 3.12). Criteria 4–7 and 10 wait on Phases 42 and 43. Two rows filed: ENH-035, ENH-036.
