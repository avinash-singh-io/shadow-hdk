---
type: Tasks
status: in-progress
---
# Phase 41 — Linux confinement — Tasks
> Mirrors `plan.md`. `[x]` done · `[/]` in-progress · `[ ]` todo.
> Verify before claiming done (Rule 12). The helper's behaviour on a kernel is verified on the
> Linux runner — this machine is macOS without Docker — and each such task cites the CI run.
> **TDD strict:** no task may be marked `[x]` without a recorded red→green.

## Group 0 — RED *(blocks)*
- [x] `tests/adapters/environment/test_linux_confinement_is_native_first.py`: the candidates in order per platform; `SHADOW_HDK_SANDBOX` narrowing and refusing an unknown name; the landlock `wrap`; two pretend candidates — the proof passes the first over and keeps the second, names both when neither confines; the mechanism on the evidence; the Linux-only proofs (skipped elsewhere)
- [x] `test_local_is_confined_for_real.py::test_which_sandbox_this_machine_has_is_reported_not_guessed` — Linux with the helper → `landlock`
- [x] `tests/test_versions.py`: the crate, its distribution and the kit's pin in lockstep
- [x] The crate's RED: `native/sandbox/Cargo.toml`, an empty `native/sandbox/src/main.rs`, `native/sandbox/src/args.rs` tests, `native/sandbox/tests/confines.rs` (Linux only)
- [x] Verify RED — 2026-09-19: the new Python file fails at import on the absent `local_sandboxes`; `test_the_linux_helper_moves_with_the_kit` fails on the absent `native/sandbox/pyproject.toml` (the 14 other tests in those files pass, 1 skips); `cargo test` fails to compile on the absent `parse`/`Command`/`Mode`/`UsageError` (8 errors), on the host and for `x86_64-unknown-linux-musl`; ruff clean

## Group 1 — The helper
- [x] `native/sandbox/`: `Cargo.toml`, `native/sandbox/src/args.rs`, `native/sandbox/src/linux.rs` (probe by raw syscall; the Landlock ruleset per mode; the seccomp filter; exec), `native/sandbox/src/main.rs` (Linux entry; a stub elsewhere), `pyproject.toml` (maturin, `bindings = "bin"`), `README.md` (the contract, the exit codes)
- [x] `.github/workflows/ci.yml`: the `native` job — fmt, clippy `-D warnings`, `cargo test` on ubuntu-latest
- [x] Verify (local) — 2026-09-19: `cargo fmt --check` clean; `cargo clippy --all-targets -- -D warnings` clean on the host, on `x86_64-unknown-linux-musl` and on `aarch64-unknown-linux-musl`; `cargo test` 9 argument tests pass (the 13 confinement tests compiled out on macOS); `cargo build --release --target x86_64-unknown-linux-musl` (rust-lld) links a 458 KB static-pie ELF
- [x] Verify (CI) — 2026-09-19: the `native` job green on `1d4145a` — fmt, clippy `-D warnings`, 9 argument tests and **12 confinement tests** passed on the ubuntu-24.04 image (Landlock ABI 7 reported by `--probe`): a write outside denied and no file left, inside allowed in every root and nothing between them, `read-only` denying the root while `/dev/null` writes, reads open everywhere, `AF_INET`/`AF_INET6` refused and `AF_UNIX` kept, `io_uring_setup` → `EPERM`, the exit code through, 127 named, 121 with the usage, environment and cwd carried — https://github.com/avinash-singh-io/shadow-hdk/actions/runs/35460151424/job/105942432468

## Group 2 — The machine's mechanisms, the proof deciding
- [x] `runtime/environment.py`: `Isolation.mechanism`; `capabilities_of` names it in the evidence
- [x] `adapters/environment/local.py`: `LocalSandbox.detail`; `local_sandboxes()` (helper via env → scripts dir → `PATH`, kept when `--probe` exits 0; then `bwrap`; seatbelt on darwin); `SHADOW_HDK_SANDBOX`; the landlock `wrap`; `LocalEnvironment.open` proving each candidate and keeping the first proven, refusing naming each tried; `_prove` stamps the mechanism
- [x] `backends.py`: `prove_box` stamps the mechanism where the backend has a name
- [x] `pyproject.toml`: the Linux dependency with its marker; the uv workspace member and source; `uv lock`
- [x] CI: `check` builds the helper and asserts landlock in force; the `bubblewrap` job (sysctl, apt, `SHADOW_HDK_SANDBOX`, asserts bubblewrap); the `macos` job
- [x] Verify (local, macOS) — 2026-09-19: `tests/adapters/environment tests/wire tests/serve tests/test_versions.py tests/invariants` **395 passed** on 3.12 and **395 passed** on 3.14.6; the full non-live suite 1,799 passed on 3.12; ruff check + format clean; mypy 461 files clean; `uv lock` resolved the workspace member; `uv sync --all-packages` built the helper with maturin on macOS and it refused honestly (120, `supported: false`) while detection listed seatbelt alone; mutations — the verdict ignored → 2 fail (passed-over, names-each-tried); the mechanism not stamped → 2 fail (passed-over, the evidence)
- [ ] Verify (CI): `check` (landlock), `bubblewrap` (bubblewrap) and `macos` (seatbelt) green; run URL: _(…)_

## Group 3 — Publish, docs, release
- [ ] `publish.yml`: the `helper` matrix (maturin-action, manylinux_2_17 and musllinux_1_2, x86_64 and aarch64, the sdist); one `uv publish` over both artifact sets; the smoke asserts landlock in force after the fresh install
- [ ] Docs: the 0.33 note under `docs/migrations/`; `docs/packages/adapters-environment.md`; `docs/for-a-product.md`'s caveat; README's platform line
- [ ] Backlog rows; Epic 0010 criteria 1–3 and 9 recorded; `[ARCH_CHANGE]` for `specs/architecture/adapters.md`
- [ ] Version 0.33.0 everywhere the versions test looks; `EXPECTED` and its docstring; `uv lock`; changelog; status row
- [ ] Verify: the four-zero gate on 3.12 and 3.14; the cargo gate; `momentum okf check .`; the wheel installed fresh on macOS pulls nothing extra; all four CI jobs green on the release commit; `/complete-phase` → STOP at the gate
