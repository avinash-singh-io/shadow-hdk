# shadow-hdk-linux-sandbox

Shadow HDK's Linux confinement helper — the first executable of the kit's OS layer (Epic 0010,
D123). `LocalEnvironment` invokes it exactly as it invokes `sandbox-exec` on macOS: the helper
confines *itself* and `exec`s the command, so there is one process, in the leash's process group,
exiting with the command's own code.

```
shadow-hdk-linux-sandbox --mode read-only|workspace-write [--root <dir>]... -- <argv>...
shadow-hdk-linux-sandbox --probe
```

## What it applies

- **Landlock** (a kernel LSM any unprivileged process may apply to itself; Linux 5.13+, ABI 4 on
  Ubuntu 24.04's 6.8): reads everywhere — the interpreter has to read its own installation;
  writes beneath each `--root` for `workspace-write` and nowhere for `read-only`; the null, zero,
  full, random, urandom, tty, ptmx and pts devices writable in both modes, because devices are not
  files (`git` opens `/dev/null` read-write at startup); TCP `bind` and `connect` handled and
  denied where the kernel has it (ABI 4+).
- **seccomp**: `socket()` with any domain but `AF_UNIX` fails with `EPERM`, and so does
  `io_uring_setup` — io_uring can open and connect sockets without a `socket` syscall, so a filter
  that stopped at `socket` would stop nothing. Every other syscall is allowed; the filesystem is
  Landlock's.

No namespaces, no root, no daemon — which is what survives Ubuntu 24.04's default AppArmor policy,
where bubblewrap's unprivileged user namespace does not. Bubblewrap stays behind it as the
fallback on a kernel without Landlock; the kit's D36 proof decides which is in force by watching
a write outside denied, a socket refused and a write inside land, before any confined mode opens.
Nothing here is trusted for having run.

## Exit codes

| code | meaning |
|---|---|
| the command's | after `exec`, the helper *is* the command |
| **120** | cannot confine — no Landlock (absent or `lsm=` without it), a ruleset the kernel did not enforce, seccomp refused; stderr says why |
| **121** | usage — the arguments above are the contract; `full` never reaches the helper |
| **126** / **127** | the command could not be executed / was not found |

`--probe` prints one JSON line — `{"version": "…", "landlock_abi": N, "supported": true|false}` —
and exits 0 or 120.

## Building

```
cargo build --release
cargo test            # the argument tests everywhere; the confinement tests on a Linux kernel
```

Packaged for PyPI by maturin (`bindings = "bin"`): one `py3-none-<platform>` wheel per OS × arch,
no Python-version coupling. `shadow-hdk` depends on it where `sys_platform == 'linux'`. Off Linux
the binary builds and refuses with 120 — so the crate lints, unit-tests and packages on any
developer machine.

Environment variables the *kit* reads (not the helper): `SHADOW_HDK_LINUX_SANDBOX` names the
helper's path when it is not beside the interpreter or on `PATH`; `SHADOW_HDK_SANDBOX` narrows the
kit's candidates to one mechanism (`landlock`, `bubblewrap`, `seatbelt`).
