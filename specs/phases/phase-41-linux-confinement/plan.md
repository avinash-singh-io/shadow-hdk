---
type: Plan
status: in-progress
---

# Phase 41 — Linux confinement — Plan

```
# Sequential:  Group 0 → Group 1 → Group 2 → Group 3
```

TDD strict (Rule 13): every group opens RED and no task is marked done without a recorded
red → green. The four-zero gate (`ruff check`, `ruff format --check`, `mypy`, `pytest -m 'not live'`)
runs per group on 3.12; the final gate also on 3.14. The crate's gate is `cargo fmt --check`,
`cargo clippy --all-targets -- -D warnings`, `cargo test`. **This machine is macOS and has no
Docker**: the helper's behaviour on a kernel is verified by the Linux runner, and each group that
touches it cites the CI run rather than claiming from a local build — Rule 12 says so explicitly.

## Reference specs

`specs/architecture/adapters.md` §the environment (`LocalEnvironment` wraps every command in the OS
sandbox; the proof at construction), `runtime.md` (the leash — unchanged here), `testing.md`
(contract suites; skips that say why). `specs/research/2026-09-19-cross-platform-grounding.md` §2
is the grounding for Landlock-first; Epic 0010 D123–D126, D133, D135 the decisions.

## The helper's contract (settled here, used by Groups 1 and 2)

```
shadow-hdk-linux-sandbox --mode read-only|workspace-write [--root <dir>]... -- <argv>...
shadow-hdk-linux-sandbox --probe
```

- The process applies Landlock (reads everywhere; writes beneath each `--root` for
  `workspace-write`; the null, zero, random, urandom, tty and pts devices writable in both modes —
  devices are not files, BUG-023; TCP `bind`/`connect` handled and denied where the ABI ≥ 4) and a
  seccomp filter (`socket` with a domain other than `AF_UNIX` → `EPERM`; `io_uring_setup` →
  `EPERM`, since io_uring would make sockets past seccomp), then `execvp`s `<argv>` — one process,
  the leash's process group, the child's exit code.
- `--probe` prints one JSON line — `{"version": "…", "landlock_abi": N, "supported": true|false}`
  — and exits 0 when the kernel has Landlock (ABI ≥ 1) and the filter can be built, else **120**.
- **120** — cannot confine (no Landlock, a ruleset the kernel did not enforce, seccomp refused);
  stderr names why. **121** — usage. **126** / **127** — the command could not be executed / was
  not found (the shell's convention). Anything else is the child's.
- `full` never reaches the helper: `LocalSandbox.wrap` returns the argv untouched for it.

## Group 0 — RED *(sequential, blocks)*

- **The mechanisms, in order, the proof deciding** (`tests/adapters/environment/test_linux_confinement_is_native_first.py`):
  `local_sandboxes()` on a pretend Linux with a helper that answers `--probe` and `bwrap` on
  `PATH` → `["landlock", "bubblewrap"]`; without the helper → `["bubblewrap"]`; on darwin →
  `["seatbelt"]`; `local_sandbox()` is the first. `SHADOW_HDK_SANDBOX=bubblewrap` narrows to that
  one; an unknown name raises naming the known ones. `LocalSandbox("landlock", …).wrap` builds
  `[helper, "--mode", mode, "--root", …, "--", *argv]` with every root for `workspace-write`, no
  root for `read-only`, argv untouched for `full`. Two pretend candidates, the first confining
  nothing and the second the machine's real box → `open` succeeds with
  `isolation.mechanism == real.name`; two confining nothing → `CannotEnforce` naming both. The
  evidence: `capabilities_of(Isolation(…, mechanism="landlock"), "workspace-write")` carries
  `landlock` in its `writes` and `network` evidence; `env.capabilities.evidence` on this machine
  carries the mechanism in force.
- **Linux, for real** (same file, `skipif(sys.platform != "linux")`): with the helper present and
  nothing narrowing, `local_sandbox().name == "landlock"` and `open(workspace-write)` proves; a
  `run_shell` write outside leaves no file; a socket is refused; `echo x > /dev/null` exits 0 in
  `read-only`; a write under `TMPDIR` (the root) lands; the helper's `--probe` JSON parses with
  `supported is True`.
- **Which sandbox this machine has** — `test_which_sandbox_this_machine_has_is_reported_not_guessed`
  in `test_local_is_confined_for_real.py` amended: Linux with the helper → `landlock`.
- **Lockstep** (`tests/test_versions.py`): `native/sandbox/Cargo.toml` and
  `native/sandbox/pyproject.toml` at `EXPECTED`; the kit's dependency on
  `shadow-hdk-linux-sandbox` pinned `== EXPECTED` under the Linux marker.
- **The crate's RED**: `native/sandbox/Cargo.toml` (package `shadow-hdk-sandbox`, bin
  `shadow-hdk-linux-sandbox`), `src/main.rs` empty of the modules, `src/args.rs` tests (mode,
  roots, `--probe`, `--`, the usage error), `tests/confines.rs` (Linux only: probe → JSON and
  exit 0 / 120; outside denied; inside allowed; socket refused; `/dev/null` writable in
  `read-only`; a child's exit code through; not-found → 127).
- Verify: the Python file fails on the absent names (`local_sandboxes`, `mechanism`); the versions
  test fails on the absent crate; `cargo test` fails to compile on the absent `args`.

**Commit:** `test: Phase 41 RED — Linux confinement, native first`

## Group 1 — The helper *(sequential)*

- `native/sandbox/Cargo.toml`: edition 2024, `[[bin]] name = "shadow-hdk-linux-sandbox"`,
  `[target.'cfg(target_os = "linux")'.dependencies]` `landlock = "0.4"`, `seccompiler = "0.5"`,
  `libc = "0.2"`; `[profile.release]` `strip`, `lto`, `codegen-units = 1`, `panic = "abort"`.
- `src/args.rs`: `Args { probe, mode, roots, argv }` from `std::env::args_os`, no clap; `Mode` from
  its two names; errors carry the usage line.
- `src/linux.rs`: `probe()` — `landlock_create_ruleset(NULL, 0, LANDLOCK_CREATE_RULESET_VERSION)`
  by raw syscall for the ABI; `confine(mode, roots)` — the `landlock` crate's `Ruleset` with
  `AccessFs::from_all(abi)` handled, `path_beneath_rules` for `/` (read), the roots (all, for
  `workspace-write`), the devices (all); `AccessNet::from_all(abi)` handled with no rule where
  ABI ≥ 4; `restrict_self()` and `RulesetStatus::NotEnforced` → exit 120; then `seccompiler`'s
  filter for the running arch, `apply_filter`; then `execvp`. `src/main.rs`: the Linux entry, and
  on any other OS a stub that says the helper confines on Linux only and exits 121 (so the crate
  builds, lints and unit-tests on the development machine and under `uv sync --all-packages`).
- `native/sandbox/pyproject.toml`: `[build-system] maturin>=1.7,<2`, `[project] name =
  "shadow-hdk-linux-sandbox"`, the version, `[tool.maturin] bindings = "bin", strip = true`;
  `native/sandbox/README.md`: the contract above, the exit codes, what is and is not confined.
- `.github/workflows/ci.yml` gains the `native` job (ubuntu-latest: `dtolnay/rust-toolchain@stable`
  with `clippy, rustfmt`; fmt, clippy, test) — added in this group so the Linux integration tests
  run on this group's push.
- Verify (local): `cargo fmt --check`; `cargo clippy --all-targets -- -D warnings` on the host and
  `--target x86_64-unknown-linux-musl`; `cargo test` (the argument tests; the Linux tests compiled
  out); `cargo build --release --target x86_64-unknown-linux-musl` links. Verify (CI): the `native`
  job green on the pushed commit — `tests/confines.rs` watched the binary deny and allow on a
  kernel; the run's URL recorded in `tasks.md`.

**Commit:** `feat(native): the Linux helper — Landlock and seccomp applied before exec (Epic 0010 D123, D133)`

## Group 2 — The machine's mechanisms, the proof deciding *(sequential)*

- `runtime/environment.py`: `Isolation.mechanism: str = ""` — the name of what was watched denying;
  `capabilities_of` names it in the `writes` and `network` evidence when set (`"landlock confines
  writes"` rather than `"isolation confines writes"`); `Isolation.none()` unchanged.
- `adapters/environment/local.py`: `LocalSandbox(name, binary, detail="")`; `local_sandboxes()
  -> list[LocalSandbox]` — darwin: seatbelt; linux: the helper (found as `SHADOW_HDK_LINUX_SANDBOX`,
  then beside the interpreter in `sysconfig`'s scripts dir, then on `PATH`; kept only when
  `--probe` exits 0, the ABI in `detail`), then `bwrap`; `SHADOW_HDK_SANDBOX` narrows to one name
  or raises; `local_sandbox()` the first or `None`. `wrap` for `landlock` per the contract.
  `LocalEnvironment.open`: for each candidate, `_prove`; keep the first with `proven`; on none,
  `CannotEnforce` listing each name with what the proof did not see — the hint for no candidate at
  all names the three mechanisms and the sysctl for bubblewrap on Ubuntu 24.04. `_prove` stamps
  `mechanism=box.name`. `LocalEnvironment` keeps `_box` (the one proven) for `_run` and
  `_prove_now`.
- `backends.py`: `prove_box` stamps `mechanism` with the backend's name where it has one (additive;
  `""` otherwise).
- `pyproject.toml`: `shadow-hdk-linux-sandbox==<version>; sys_platform == 'linux' and
  platform_machine in 'x86_64 aarch64'` under `dependencies`; `[tool.uv.workspace] members =
  ["native/sandbox"]`; `[tool.uv.sources]` the member; `uv lock`.
- CI: the `check` job installs the stable toolchain so `uv sync` builds the helper, then asserts
  `local_sandbox().name == "landlock"` before the suite; a `bubblewrap` job (`sudo sysctl -w
  kernel.apparmor_restrict_unprivileged_userns=0`, `apt-get install bubblewrap`,
  `SHADOW_HDK_SANDBOX=bubblewrap`, the same assertion for `bubblewrap`, the suite minus the
  benchmark); a `macos` job (macos-latest, the suite minus the benchmark, no Postgres — its
  contract suites skip and say so).
- Verify (local, macOS): `uv run pytest tests/adapters/environment tests/wire tests/serve
  tests/test_versions.py -q` green on 3.12 and 3.14; mutations — the proof's verdict ignored (the
  first candidate kept) → the pretend test fails; the mechanism not stamped → the evidence test
  fails. Verify (CI): `check` green with landlock in force, `bubblewrap` green with bubblewrap in
  force, `macos` green — the run's URL recorded.

**Commit:** `feat(environment): Linux confinement is native first — the helper, bubblewrap behind it, the proof deciding (D133)`

## Group 3 — Publish, docs, release *(sequential, last)*

- `.github/workflows/publish.yml`: a `helper` job on `PyO3/maturin-action` over
  `{x86_64, aarch64} × {manylinux_2_17, musllinux_1_2}` plus the sdist, uploaded as artifacts;
  `publish` downloads both artifact sets into `dist/` and publishes them in one `uv publish`; the
  smoke asserts `shadow-hdk-linux-sandbox --probe` exits 0 and `local_sandbox().name ==
  "landlock"` on the runner after the fresh install.
- Docs: `docs/migrations/0.33.md` (what a Linux host sees now; `SHADOW_HDK_SANDBOX`;
  `Isolation.mechanism`; the dependency; the fallback's sysctl); `docs/packages/adapters-environment.md`;
  `docs/for-a-product.md`'s Linux line in the caveats; `README.md`'s platform sentence if there is
  one; `clients/typescript/README.md` unchanged (the sidecar's pin stays Phase 42's).
- Backlog: ENH rows this phase closes or files (a `[DISCOVERY]` each); Epic 0010's criteria 1–3
  and 9 ticked in its record's Amendments; the LangGraph ledger untouched.
- Version 0.33.0 everywhere the versions test looks; `EXPECTED` with its docstring entry; `uv
  lock`; changelog; the status row; `[ARCH_CHANGE]` for `specs/architecture/adapters.md`
  (additive: the Linux mechanism and the candidates' order) so `/sync-docs` finds it.
- Verify: the four-zero gate on 3.12 and 3.14; `cargo` gate; `momentum okf check .`; the wheel
  built and installed fresh on macOS (nothing extra pulled); CI green on all four jobs for the
  release commit; then `/complete-phase` and STOP at the merge/release gate.

**Commits:** `infra(publish): the Linux helper's wheels beside the kit` · `docs: 0.33 — Linux confinement, native first` · `chore(release): 0.33.0`
