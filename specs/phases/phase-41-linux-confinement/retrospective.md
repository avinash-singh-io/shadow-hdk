---
type: Retrospective
status: complete
---

# Phase 41 — Linux confinement — Retrospective

> Epic 0010's first lane, derived from the epic on 2026-09-19 and completed the same day, without
> an interview and without a Linux machine at hand. v0.33.0.

## What was delivered

- **The `shadow-hdk-sandbox` crate** (`native/sandbox`, D123) with its first helper,
  `shadow-hdk-linux-sandbox`: 458 KB static, Landlock for the filesystem and TCP, seccomp refusing
  non-`AF_UNIX` sockets and `io_uring_setup`, applied to itself before `exec` — one process, in the
  leash's process group, the command's exit code; its own codes 120 (cannot confine), 121 (usage),
  126/127 (the command); `--probe`. Twelve integration tests watch the built binary on a kernel;
  nine unit tests hold the argument contract everywhere.
- **The proof decides among the machine's mechanisms** (D133): `local_sandboxes()` in the field's
  order — the helper, then bubblewrap; seatbelt on macOS — `LocalEnvironment.open` proving each
  and keeping the first the D36 proof accepts, a refusal naming each one tried,
  `Isolation.mechanism` carrying the name onto the capability evidence, `SHADOW_HDK_SANDBOX`
  narrowing to one.
- **The helper as a distribution**: `shadow-hdk-linux-sandbox`, bin-only platform wheels
  (`py3-none-{manylinux_2_17,musllinux_1_2}_{x86_64,aarch64}`) and an sdist, built by maturin, a
  uv workspace member, a dependency of `shadow-hdk` under a Linux x86_64/aarch64 marker, in
  lockstep with the kit's version.
- **CI on every operating system the kit claims** (D126): Linux with the helper (`landlock`, 1,818
  passed with Postgres), Linux with the helper set aside (`bubblewrap` + the AppArmor sysctl, 1,799
  passed), macOS (`seatbelt`, 1,799 passed), the crate's gate, the four wheels built and the
  x86_64 one installed and watched confining — one reusable workflow shared with `publish`, which
  uploads the seven files together and asserts Landlock from the index in its smoke.
- Docs: `docs/migrations/0.33.md`, the environment guide, README, the product doc's
  operating-systems paragraph; the architecture's environment section, file structure and testing
  layers synced additively.

## What went well

- **Deriving from the epic worked as designed.** Every decision the phase needed — Landlock first,
  bubblewrap behind, the proof deciding, helpers not PyO3, proof before claim — was already in
  D122–D137. The only new decisions were shape (a platform wheel rather than "inside the artifact")
  and detail (the ABI at build time, `io_uring_setup`, the device list), each recorded in the
  history as it was made.
- **RED first paid for itself twice.** The `io_uring_setup` test was written before the filter,
  which is why the filter has it; the "a candidate that confines nothing is passed over" test is
  what makes "the proof decides" a property rather than a sentence. Both mutations (the verdict
  ignored; the mechanism not stamped) were caught by exactly the tests written for them.
- **The Linux behaviour was proven without a Linux machine** by making CI the verification and
  saying so in every task that depended on it (Rule 12). The `native` job was green on the first
  push; the wheel matrix on the first push; the `check`/`bubblewrap`/`macos` jobs on the first
  push. Nothing was claimed from a local build.
- **One definition for the wheels.** `helper-wheels.yml` is called by `ci` on every push and by
  `publish` at a release, so a release cannot discover at publish time that the cross matrix broke.

## What did not

- The document invariant caught backticked crate-relative paths (the crate's `args.rs` named without its `native/sandbox/` prefix) in the phase's own
  plan — a CI failure on the phase-start commit. Known caveat; it bit once more.
- The epic's earlier amendment had said "Phase 42's Linux half" when the helper sat in Phase 41's
  row; the membership had to be re-cut before the first lane could be derived. Loose wording in an
  amendment is a real cost the next day.
- The runner's kernel reports Landlock ABI 7, not the ABI 4 of a stock Ubuntu 24.04 6.8 kernel; the
  proof on the *exact* laptop kernel is inferred from best-effort compatibility, not measured.
  Honest in the epic's record; a stock-kernel container in CI would close it (ENH-036 territory).
- The aarch64 wheels are built and never executed (ENH-036).

## Lessons

- **A machine's confinement is a list, not a value.** `local_sandbox() -> X | None` was the wrong
  shape the moment a second mechanism existed; `local_sandboxes()` with the proof choosing is the
  shape that makes the third (Windows, Phase 43) an append.
- **"The proof decides" needs a test where the first candidate lies.** Otherwise the order is doing
  the deciding and the proof is decoration.
- **Build the helper off-Linux too.** A crate that refuses honestly with 120 on macOS is what lets
  `uv sync --all-packages`, clippy and the unit tests run on the development machine and on every
  contributor's — the alternative is a crate nobody can touch without a Linux box.
- **Name the mechanism on the evidence, not in a log line.** A product's "confined by …" is read
  from `CapabilityEvidence.source`, the thing it already reads for `proven`.

## Carried forward

- ENH-035 — Landlock ABI 6 scopes (abstract unix sockets, signals), decided with a measurement.
- ENH-036 — the aarch64 wheels on an arm runner; a stock-kernel leg.
- Phase 42 (optional): the per-OS artifact carries the same helper inside.
- Phase 43 (deferred): Windows — the leash's Job Objects, then confinement by D134's fork.
- The LangGraph ledger untouched; the B review (D129) waits on Epic 0009's close.

## Verification Evidence

Captured 2026-09-20 on the release commit `cb1acb2` (tree identical through the docs-sync commit
`70f4b74`), macOS 26 / Python 3.12.13 and 3.14.6 / Rust 1.98.1. Exit codes were read from each
tool's own summary line (the capture script's `PIPESTATUS` was empty under zsh); every command's
summary is the passing one.

### `uv sync --all-packages --all-extras` (the build command; builds the helper with maturin)

```
Prepared 1 package in 2.84s
Installed 1 package in 1ms
 + shadow-hdk-linux-sandbox==0.33.0 (from file:///Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/native/sandbox)
```

### `uv run ruff check` · `uv run ruff format --check` · `uv run mypy`

```
All checks passed!
516 files already formatted
Success: no issues found in 461 source files
```

### `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo clippy --all-targets --target x86_64-unknown-linux-musl -- -D warnings && cargo test` (in `native/sandbox`)

```
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.07s
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.04s
test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
exit=0
```

(The second line is `tests/confines.rs`, compiled out on macOS; on the Linux runner it is 12 passed
— below.)

### `uv run pytest` (the test command; the whole non-live suite, benchmark included) — 3.12

```
1803 passed, 20 skipped, 13 deselected, 85 warnings in 161.40s (0:02:41)
```

### `UV_PROJECT_ENVIRONMENT=.venv314 uv run --python 3.14 pytest` — 3.14

```
1803 passed, 20 skipped, 13 deselected, 85 warnings in 159.01s (0:02:39)
```

### `momentum okf check .`

```
✓ specs/ is an OKF v0.1 conformant bundle (210 markdown file(s))
```

### CI on the release commit — https://github.com/avinash-singh-io/shadow-hdk/actions/runs/35461278235

```
success
check: success                                  landlock in force (ABI 7); 1818 passed, 1 skipped (Postgres suites included)
bubblewrap: success                             bubblewrap in force, the helper set aside; 1799 passed, 20 skipped
macos: success                                  seatbelt in force; 1799 passed, 20 skipped
native: success                                 fmt, clippy -D warnings, 9 + 12 tests (the binary watched on the kernel)
wheels / wheel (x86_64, manylinux_2_17): success
wheels / wheel (aarch64, manylinux_2_17): success
wheels / wheel (x86_64, musllinux_1_2): success
wheels / wheel (aarch64, musllinux_1_2): success
wheels / sdist: success
wheels / installed: success                     {"landlock_abi":7,"supported":true} · confined
```

### The wheel, fresh (macOS)

```
uv build --out-dir dist                       → shadow_hdk-0.33.0-py3-none-any.whl · shadow_hdk-0.33.0.tar.gz
uv pip install … dist/shadow_hdk-0.33.0-py3-none-any.whl   (no helper pulled: the marker)
Requires-Dist: shadow-hdk-linux-sandbox==0.33.0; sys_platform == 'linux' and (platform_machine == 'x86_64' or platform_machine == 'aarch64')
initialize → {"jsonrpc": "2.0", "id": 1, "result": {"protocol_version": "3", "version": "0.33.0"}}
```
