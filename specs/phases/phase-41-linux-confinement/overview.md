---
type: Phase
status: in-progress
epic: cross-platform
tags: [linux, landlock, seccomp, bubblewrap, sandbox, rust, helper, proof, environment, ci, maturin]
deps: []
---

# Phase 41 — Linux confinement

> **Derived, not brainstormed.**
> Generated from `specs/epics/0010-cross-platform.md` on 2026-09-19 with no
> operator interview (Epic D10). Every decision below was settled when the
> epic was written and is NOT re-litigated here. Decisions are durable;
> plans are perishable — this file is the perishable half.

## Goal

A confined mode opens on Linux the way it opens on macOS today — proven, by the operating system's
own mechanism — and keeps opening on the Linux a laptop actually runs. Today the kit is
bubblewrap-only, and Ubuntu 24.04's default AppArmor policy denies the unprivileged user namespace
bubblewrap needs, so on the most common desktop Linux every confined mode refuses with
`CannotEnforce`. The field's answer (Codex's, D133) is Landlock and seccomp applied by the child to
itself before `exec` — no namespaces, no root, no daemon — with bubblewrap behind it where the
kernel is too old. Those are syscalls a process makes on itself, which the Python process cannot
make for a child; so this phase opens the `shadow-hdk-sandbox` crate (D123) with its first helper,
`shadow-hdk-linux-sandbox`, invoked by `LocalEnvironment` exactly as `sandbox-exec` is on macOS.
Nothing about the proof changes: the helper is a candidate the D36 proof watches denying and
allowing before it is trusted, and the evidence names which mechanism is in force.

The epic's amendment of 2026-09-19 puts this lane first because it is one of the two blockers for a
macOS + Linux laptop release of a product that runs the kit in-process; the other, BUG-056, shipped
in 0.32.1.

## Inherited decisions

> From the epic record. Never re-asked. D122–D137 in full on the epic; the ones this phase acts on:

- D123 — small static helper executables from one Rust crate, `shadow-hdk-sandbox`, invoked by the Python leash as `sandbox-exec` is; detection, the profile per mode, the leash's policy and the D36 proof stay in Python; PyO3 not required. *Amended 2026-09-19 for shape:* with the artifact optional, the Linux helper reaches a machine as the `shadow-hdk-linux-sandbox` distribution — one `py3-none` platform wheel per OS × arch, never one per Python version — a dependency of `shadow-hdk` under a Linux marker.
- D124 — one contract, native primitives: `Environment`, `Isolation`, `run_leashed` unchanged; Linux implements them with Landlock + seccomp (bubblewrap fallback).
- D125 — proof before claim: every mechanism is watched denying and allowing before a confined mode opens; where none is proven the mode refuses with `CannotEnforce`, never a silent `full`.
- D126 — the same suites on every runner the kit claims; a red runner blocks the release. This phase claims Linux and macOS.
- D128 — the engine and the ecosystem unchanged.
- D133 — Landlock + seccomp in-process by the helper, bubblewrap the fallback, **the proof deciding which is in force**; the `landlock` crate probes the kernel for the highest ABI.
- D135 — consume the OS primitives (`landlock`, `seccompiler`), own the proof.

## Scope

**In:**

- The `shadow-hdk-sandbox` crate under `native/sandbox/`: the `shadow-hdk-linux-sandbox` binary — `--mode read-only|workspace-write`, `--root <path>` (repeatable), `--probe`, `-- <argv>`; Landlock (filesystem: reads everywhere, writes beneath the roots and to the null, zero, random and tty devices; TCP bind/connect denied where the ABI has it) and seccomp (a non-`AF_UNIX` `socket` and `io_uring_setup` refused with `EPERM`) applied to itself, then `execvp`; distinct exit codes when it cannot confine (120) or is misused (121); the child's exit code otherwise. Rust unit tests for the arguments and Linux integration tests that watch the built binary deny and allow.
- The helper packaged as the `shadow-hdk-linux-sandbox` distribution with maturin (`bindings = "bin"`), a uv workspace member, a dependency of `shadow-hdk` where `sys_platform == 'linux'` on x86_64 / aarch64; the version in lockstep (`tests/test_versions.py`).
- `adapters/environment/local.py`: the machine's mechanisms as an ordered list of candidates — the helper (found beside the interpreter, then on `PATH`, `--probe` saying the kernel supports it), then bubblewrap, seatbelt on macOS — with `LocalEnvironment.open` proving each in turn and keeping the first the proof accepts; a refusal naming every mechanism tried; `SHADOW_HDK_SANDBOX` narrowing the candidates to one for an operator or a CI job.
- `Isolation.mechanism` — the name of what was watched denying — carried into the capability evidence so a host reads "landlock" or "bubblewrap" or "seatbelt" beside `proven`.
- CI: the Linux `check` job builds the helper and asserts Landlock is in force; a `bubblewrap` job sets the helper aside (`SHADOW_HDK_SANDBOX`) and the AppArmor sysctl and runs the suite on the fallback; a `macos` job runs the suite on seatbelt; a `native` job runs `cargo fmt --check`, `clippy -D warnings` and `cargo test` on Linux. The publish workflow builds the helper's wheels (manylinux and musllinux, x86_64 and aarch64) and publishes them beside the kit; the fresh-install smoke asserts Landlock is in force on the runner.
- Docs: the 0.33 note under `docs/migrations/`, `docs/packages/adapters-environment.md`, `docs/for-a-product.md`'s caveat, the crate's README (the CLI contract); `[ARCH_CHANGE]` for `specs/architecture/adapters.md` synced at completion.

**Out:** the per-OS artifact (Phase 42, optional); Windows — the leash's Job Objects and confinement (Phase 43, deferred); network egress through a proxy (D137); any change to the leash's POSIX primitives; the engine (D128).

## Deliverables

| Deliverable | Verification |
|---|---|
| `native/sandbox/` — the crate, its README, `pyproject.toml` | `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test` on the Linux runner (the `native` job); locally on macOS the argument tests and a `--target x86_64-unknown-linux-musl` check |
| `LocalEnvironment` choosing among candidates, the proof deciding, the evidence naming | `uv run pytest tests/adapters/environment tests/wire tests/serve -q` on 3.12 and 3.14 (macOS: seatbelt); the Linux `check` job (landlock) and `bubblewrap` job |
| The helper as a dependency of the kit on Linux, in lockstep | `tests/test_versions.py`; `uv lock` resolving; the fresh-install smoke on the Linux runner after publish |
| CI on Linux (two ways) and macOS; the publish workflow building the helper's wheels | the four jobs green on the phase branch; `publish.yml` dry-run to TestPyPI is the owner's call |
| Docs and the migration note | `momentum okf check .`; the doc-invariant tests |

## Acceptance criteria

> Checkable. "It works" is not a criterion.

1. On the Linux runner with Ubuntu 24.04's default AppArmor, `LocalEnvironment.open(root, mode="workspace-write")` returns with `isolation.proven is True` and `isolation.mechanism == "landlock"`; a `run_shell` write outside the root leaves no file and exits non-zero; a socket is refused; a write inside lands (epic criterion 3, first half).
2. On the same runner with `SHADOW_HDK_SANDBOX=bubblewrap` and the sysctl set, the same opens with `mechanism == "bubblewrap"` (epic criterion 3, second half — the fallback, proven, and said).
3. A candidate that confines nothing is passed over for one that does, and when none does the refusal names each mechanism tried and why (D133's "the proof deciding", tested with pretend mechanisms on any OS).
4. The capability evidence a host reads carries the mechanism's name beside `proven`.
5. The `native` job is green: the crate formatted, clippy-clean at `-D warnings`, its Linux integration tests watching the binary deny a write outside, deny a socket, allow a write inside, pass a child's exit code through and exit 120 when it cannot confine (proven by `--probe` on a kernel without Landlock, or the exit code's path unit-tested where no such kernel is at hand).
6. `pip install shadow-hdk==0.33.0` on Linux x86_64 or aarch64 installs the helper; on macOS it installs nothing extra; `tests/test_versions.py` holds the crate, its distribution and the kit's pin to one number.
7. The full non-live suite is green on the Linux runner (both ways) and on the macOS runner; the count does not drop (epic criterion 9); mypy and ruff clean; `momentum okf check .` conformant.
8. The engine untouched: no Rust below the OS layer; `Harness`, `Thread`, `run()` signatures unchanged; `runtime/leash.py` and `runtime/processes.py` unchanged.

## Run policy (inherited)

release: per-phase · push: per-phase · tdd: strict
