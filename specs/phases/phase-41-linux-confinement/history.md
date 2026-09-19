---
type: History
status: in-progress
epic: cross-platform
---

# phase-41-linux-confinement — History

### [SCOPE_CHANGE] 2026-09-19 — Epic 0010's membership re-cut; this lane is Phase 41, Linux confinement
Topics: epic, membership, linux, landlock, artifact, windows
Affects-phases: phase-41-linux-confinement, phase-42-the-artifact, phase-43-windows
Affects-specs: epics/0010-cross-platform.md#phases-and-dependencies, planning/roadmap.md, phases/README.md
Detail: The owner's order after the field survey (Linux confinement first; the artifact optional; Windows deferred) did not match the epic's phase list, which had the Linux helper inside "41 — the OS layer" beside Windows process control and called the next lane "Phase 42's Linux half". The list is now `phase-41-linux-confinement` (this lane), `phase-42-the-artifact` (optional, deps 41) and `phase-43-windows` (deferred, deps 41, absorbing the Job Objects). Recorded as the epic's second amendment; D122–D137 unchanged.

---

### [DECISION] 2026-09-19 — The helper reaches a Linux machine as a platform wheel, not only inside the artifact
Topics: distribution, maturin, wheel, landlock, helper, d123
Affects-phases: phase-41-linux-confinement, phase-42-the-artifact
Affects-specs: epics/0010-cross-platform.md#amendments
Detail: D123 said helpers ship inside the artifact so there is no wheel per Python × OS × arch. With the artifact optional, the Linux helper has to reach a `pip install shadow-hdk` on Linux some other way: the `shadow-hdk-linux-sandbox` distribution, built by maturin with `bindings = "bin"` — one `py3-none` wheel per OS × arch, no Python-version coupling, which is what D123 actually declined — and a dependency of the kit under `sys_platform == 'linux' and platform_machine in 'x86_64 aarch64'` (other Linux architectures keep the bubblewrap path rather than failing to install). Versions in lockstep with the kit (the versions test). The artifact, when it comes, carries the same binary.

---

### [DECISION] 2026-09-19 — The helper's contract, and the proof choosing among candidates
Topics: landlock, seccomp, bubblewrap, proof, d133, contract, exit-codes
Affects-phases: phase-41-linux-confinement
Affects-specs: architecture/adapters.md#the-environment
Detail: `shadow-hdk-linux-sandbox --mode <m> [--root <dir>]... -- <argv>` applies Landlock (reads everywhere; writes beneath the roots for `workspace-write`; the null/zero/random/tty/pts devices writable in both confined modes — BUG-023's rule kept; TCP bind/connect denied where the ABI has it) and seccomp (`socket` outside `AF_UNIX` and `io_uring_setup` → `EPERM`) to itself and `execvp`s — one process, the child's exit code; `--probe` reports the ABI as JSON; 120 when it cannot confine, 121 for usage, 126/127 for a command that cannot run. On the Python side `local_sandboxes()` lists the machine's mechanisms in the field's order (the helper, then bubblewrap; seatbelt on macOS), `LocalEnvironment.open` proves each in turn and keeps the first the D36 proof accepts, `Isolation.mechanism` names it on the evidence, and `SHADOW_HDK_SANDBOX` narrows the candidates to one for an operator or a CI job. The leash is untouched: the helper is exec'd inside the same process group `sandbox-exec` is.

---

### [NOTE] 2026-09-19 — G0 RED: what the phase must make true, written down first
Topics: tdd, red, landlock, proof, evidence, lockstep
Affects-phases: phase-41-linux-confinement
Affects-specs: none
Detail: Twenty Python tests — the candidates per platform, the operator's narrowing, the helper's argv, the proof passing a candidate over and naming each tried, the mechanism on the evidence, and six that run only on a Linux kernel with the helper installed (the CI runner) — plus the lockstep test and the crate's own: eight argument tests and thirteen integration tests that watch the built binary deny a write outside, allow one inside and in every root, deny a write in `read-only` while `/dev/null` stays writable, refuse `AF_INET`/`AF_INET6` and keep `AF_UNIX`, refuse `io_uring_setup` with `EPERM`, pass the child's exit code through, name a missing command at 127, say the usage at 121, and carry the environment and the working directory. The `io_uring` test is there because seccomp does not see io_uring operations: a runtime that blocked `socket` and left `io_uring_setup` open would have blocked nothing.

---
