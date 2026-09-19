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
- [ ] `tests/adapters/environment/test_linux_confinement_is_native_first.py`: the candidates in order per platform; `SHADOW_HDK_SANDBOX` narrowing and refusing an unknown name; the landlock `wrap`; two pretend candidates — the proof passes the first over and keeps the second, names both when neither confines; the mechanism on the evidence; the Linux-only proofs (skipped elsewhere)
- [ ] `test_local_is_confined_for_real.py::test_which_sandbox_this_machine_has_is_reported_not_guessed` — Linux with the helper → `landlock`
- [ ] `tests/test_versions.py`: the crate, its distribution and the kit's pin in lockstep
- [ ] The crate's RED: `native/sandbox/Cargo.toml`, an empty `src/main.rs`, `src/args.rs` tests, `tests/confines.rs` (Linux only)
- [ ] Verify RED: the Python tests fail on the absent names; the versions test on the absent crate; `cargo test` fails to compile on the absent `args`

## Group 1 — The helper
- [ ] `native/sandbox/`: `Cargo.toml`, `src/args.rs`, `src/linux.rs` (probe by raw syscall; the Landlock ruleset per mode; the seccomp filter; exec), `src/main.rs` (Linux entry; a stub elsewhere), `pyproject.toml` (maturin, `bindings = "bin"`), `README.md` (the contract, the exit codes)
- [ ] `.github/workflows/ci.yml`: the `native` job — fmt, clippy `-D warnings`, `cargo test` on ubuntu-latest
- [ ] Verify (local): `cargo fmt --check`; clippy on the host and on `x86_64-unknown-linux-musl`; `cargo test`; a release build for the musl target links
- [ ] Verify (CI): the `native` job green — `tests/confines.rs` watched the binary deny and allow on the runner's kernel; run URL: _(…)_

## Group 2 — The machine's mechanisms, the proof deciding
- [ ] `runtime/environment.py`: `Isolation.mechanism`; `capabilities_of` names it in the evidence
- [ ] `adapters/environment/local.py`: `LocalSandbox.detail`; `local_sandboxes()` (helper via env → scripts dir → `PATH`, kept when `--probe` exits 0; then `bwrap`; seatbelt on darwin); `SHADOW_HDK_SANDBOX`; the landlock `wrap`; `LocalEnvironment.open` proving each candidate and keeping the first proven, refusing naming each tried; `_prove` stamps the mechanism
- [ ] `backends.py`: `prove_box` stamps the mechanism where the backend has a name
- [ ] `pyproject.toml`: the Linux dependency with its marker; the uv workspace member and source; `uv lock`
- [ ] CI: `check` builds the helper and asserts landlock in force; the `bubblewrap` job (sysctl, apt, `SHADOW_HDK_SANDBOX`, asserts bubblewrap); the `macos` job
- [ ] Verify (local, macOS, 3.12 and 3.14): `tests/adapters/environment tests/wire tests/serve tests/test_versions.py` green; mutations — verdict ignored → the pretend test fails; mechanism not stamped → the evidence test fails
- [ ] Verify (CI): `check` (landlock), `bubblewrap` (bubblewrap) and `macos` (seatbelt) green; run URL: _(…)_

## Group 3 — Publish, docs, release
- [ ] `publish.yml`: the `helper` matrix (maturin-action, manylinux_2_17 and musllinux_1_2, x86_64 and aarch64, the sdist); one `uv publish` over both artifact sets; the smoke asserts landlock in force after the fresh install
- [ ] Docs: `docs/migrations/0.33.md`; `docs/packages/adapters-environment.md`; `docs/for-a-product.md`'s caveat; README's platform line
- [ ] Backlog rows; Epic 0010 criteria 1–3 and 9 recorded; `[ARCH_CHANGE]` for `specs/architecture/adapters.md`
- [ ] Version 0.33.0 everywhere the versions test looks; `EXPECTED` and its docstring; `uv lock`; changelog; status row
- [ ] Verify: the four-zero gate on 3.12 and 3.14; the cargo gate; `momentum okf check .`; the wheel installed fresh on macOS pulls nothing extra; all four CI jobs green on the release commit; `/complete-phase` → STOP at the gate
