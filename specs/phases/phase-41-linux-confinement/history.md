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

### [NOTE] 2026-09-19 — G1: the helper, and three choices inside it
Topics: landlock, seccomp, io_uring, abi, devices, exit-codes, maturin
Affects-phases: phase-41-linux-confinement
Affects-specs: none
Detail: (1) The Landlock ABI is a build-time choice, `ABI::V5`, per the crate's own guidance — never derived from the running kernel — with best-effort compatibility below it; a kernel that enforces nothing is exit 120, a kernel that enforces part (ABI 4 on Ubuntu 24.04) is accepted and the Python proof decides. (2) seccomp refuses `io_uring_setup` beside non-`AF_UNIX` `socket`: io_uring can create and connect sockets without a `socket` syscall since 5.19, so the field's usual "block the socket syscalls" leaves a door; the integration test asserts `EPERM` on it. (3) `/dev/full`, `/dev/ptmx` and `/dev/pts` join BUG-023's device list on Linux — a command given a pseudo-terminal, or allocating one, must be able to write it. The helper is 458 KB as a static-pie musl binary; the crate builds and refuses honestly (120) off Linux so it lints, unit-tests and packages on any machine.

---

### [ARCH_CHANGE] 2026-09-19 — G2: the environment chooses among the machine's mechanisms; the evidence names one
Topics: sandbox, environment, mechanism, landlock, bubblewrap, seatbelt, evidence, distribution
Affects-phases: phase-41-linux-confinement
Affects-specs: architecture/adapters.md#the-environment
Detail: `specs/architecture/adapters.md` says `LocalEnvironment` wraps every command in `sandbox-exec` (macOS) or bubblewrap (Linux). Additive change for `/sync-docs`: on Linux the first candidate is the kit's `shadow-hdk-linux-sandbox` helper (Landlock + seccomp, found beside the interpreter, on `PATH` or by `SHADOW_HDK_LINUX_SANDBOX`, kept when `--probe` says the kernel has Landlock), bubblewrap second; `local_sandboxes()` lists the candidates in that order, `LocalEnvironment.open` proves each and keeps the first the proof accepts, a refusal names each one tried, and `Isolation.mechanism` puts the name on the capability evidence (`landlock confines writes`). `SHADOW_HDK_SANDBOX` narrows to one name. The helper is a dependency of `shadow-hdk` under a Linux x86_64/aarch64 marker, a uv workspace member built by maturin at sync. The leash, `Environment`, `Isolation`'s other fields and `run_leashed` are unchanged (D124).

---

### [DECISION] 2026-09-19 — The whole suite runs on the fallback, and macOS is a runner
Topics: ci, bubblewrap, macos, d126
Affects-phases: phase-41-linux-confinement
Affects-specs: none
Detail: The `bubblewrap` job runs the full non-live suite with `SHADOW_HDK_SANDBOX=bubblewrap`, not the environment's tests alone — a mechanism that passes the environment's proof and fails a served thread's is not a fallback. The `macos` job runs the same suite on seatbelt; the Postgres contract suites skip there and say so. With `native`, four jobs; a red one blocks a release (D126). The `check` job asserts `landlock` is the mechanism in force before the suite, `bubblewrap` asserts its own, `macos` asserts seatbelt — so a runner that silently fell back would fail its assertion, not pass a weaker proof.

---

### [DECISION] 2026-09-19 — G3: the helper's wheels are built on every push, by one workflow
Topics: ci, publish, maturin, wheels, distribution
Affects-phases: phase-41-linux-confinement, phase-42-the-artifact
Affects-specs: none
Detail: The four platform wheels and the sdist are built by `helper-wheels.yml`, a reusable workflow `ci` calls on every push and `publish` calls at a release — one definition, so a release never finds out at publish time that the cross matrix broke, and the x86_64 glibc wheel is installed into a fresh venv on the runner to probe and confine for real before anything is published. The aarch64 wheels are built and not run (ENH-036: an arm runner). `publish` uploads seven files in one `uv publish` so the index lists the helper the moment it lists the kit, and the fresh-install smoke asserts Landlock from the index.

---

### [DISCOVERY] 2026-09-19 — Two rows from the helper's design
Topics: landlock, scope, aarch64, ci
Affects-phases: phase-42-the-artifact
Affects-specs: none
Detail: ENH-035 — Landlock ABI 6 can scope abstract unix sockets and signals to the sandbox; the helper keeps `AF_UNIX` whole today (Codex's exemption) so a confined command could signal its parent or reach a desktop's D-Bus; decide with a measurement of what breaks. ENH-036 — the aarch64 wheels are never executed in CI; GitHub's arm runners are free for public repositories.

---
