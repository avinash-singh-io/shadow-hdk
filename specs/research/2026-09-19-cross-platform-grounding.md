---
type: Research
status: complete
date: 2026-09-19
epic: cross-platform
---

# Cross-platform grounding — how the field ships and confines on three operating systems

> Read before Epic 0010's decisions were written, so that none of them is an invention. Each row
> below was checked against a current source on 2026-09-19; the sources are at the end. The
> question was threefold: how do comparable systems *ship* across macOS, Windows and Linux; how do
> they *confine* a process on each; and what do they do when they cannot.

## 1. Distribution — everyone ships a runtime inside a per-platform binary

| system | language | how it ships | size | Windows |
|---|---|---|---|---|
| **Claude Code** (v2.1.113, 2026-04) | TypeScript | `bun build --compile` → a native binary per platform; npm `optionalDependencies` per platform + a postinstall that links the binary; `claude.ai/install.sh` and `install.ps1`; eight targets including `win32-x64`, `win32-arm64` and musl | **~100 MB** — "most of it is JavaScriptCore and Bun's APIs, not Claude Code's actual code" | native, yes |
| **Codex** | Rust | native binary per platform; npm and brew | small | native, yes |
| **OpenCode** | TypeScript | Bun-compiled single binary per platform; npm postinstall selects it | large | "in progress" — Bun-version and `node`-shim defects on Windows |
| **Temporal SDKs** | Rust core | one Rust core, thin FFI bridges, idiomatic SDKs per language; *"it's desirable from a packaging and performance perspective to have the core live in the same process as the language-specific SDK, meaning users can deploy one binary"* | — | — |

**Python's equivalents.** **PyApp** (Rust launcher; fetches a `python-build-standalone` interpreter
and installs the project with `uv` on first run, *or* embeds both for a fully offline binary at
larger size; Hatch integrates it) is the living option and the one this epic names. **PyOxidizer**
is unmaintained since 2024-03 and excluded. PyInstaller and Nuitka work but carry anti-virus false
positives and a per-release signing burden. `uvx` / `uv tool install` is the developer channel, not
the end-user one.

**How a desktop app embeds a helper.** Tauri's sidecar convention — `my-binary-$TARGET_TRIPLE`
under the app, one per target — is the shape a product's installed app would use to carry the kit's
binary.

**Signing on macOS.** Notarization rejects a bundle with any unsigned nested Mach-O: the interpreter,
every `.so` and `.dylib` must carry Developer ID, a secure timestamp and the hardened runtime, and a
Python bundle needs the *allow unsigned executable memory* entitlement. Claude Code and every
Electron application pay this bill; so will Phase 42.

**Calibration.** The field's norm for a runtime-bundled agent CLI is about 100 MB. The kit's own
numbers today: importing `shadow_hdk.serve` takes 0.45–0.64 s; the process sits at ~100 MB resident.
Phase 42's targets are set against the norm, not against a wish.

## 2. Confinement — three operating systems, three mechanisms, and a policy for when it is missing

| | macOS | Linux | Windows | when unavailable |
|---|---|---|---|---|
| **Codex** | seatbelt through `/usr/bin/sandbox-exec`, dynamically generated SBPL, default-deny | **Landlock + seccomp-BPF** primary through the `codex-linux-sandbox` helper (Landlock: reads everywhere, writes only to allow-listed directories and `/dev/null`; seccomp blocks `connect`/`bind`/`listen`/`sendto`…, `AF_UNIX` exempt); **bubblewrap fallback** where Landlock is absent; Ubuntu 24.04's AppArmor needs a sysctl | **restricted tokens + synthetic SIDs + ACLs + firewall rules + Job Objects**; production is the **elevated** model — one-time UAC, two local users (`CodexSandboxOffline`, `CodexSandboxOnline`), a four-binary chain `codex.exe → codex-sandbox-setup.exe (UAC) → codex-command-runner.exe → child (restricted token)`; the **unelevated** prototype was abandoned — "ACL setup was expensive … added noticeable latency" and network isolation was impossible without elevation | warns at startup; "the only major CLI agent that enables sandboxing by default" |
| **Claude Code** | seatbelt | bubblewrap + `socat` relaying through a **host-side proxy** with a domain allowlist; the proxy also masks credentials (sentinel in, real value out to allowed hosts) | **none natively — WSL2**: "The sandbox is built into Claude Code and runs on macOS, Linux, and WSL2. Native Windows is not supported." | "By default, if the sandbox cannot start because dependencies are missing or the platform is unsupported, Claude Code shows a warning and runs commands without sandboxing"; `sandbox.failIfUnavailable` makes it a hard failure; violations are reported "naming the path or host the sandbox denied" |
| **Anthropic `sandbox-runtime`** (srt, open source, npm) | seatbelt | bubblewrap | — | a Node library wrapping any command or MCP server with the same two mechanisms plus the proxy; reference material for this kit, not consumable from Python or Rust |

**Known failure modes on Windows** (Codex): anti-virus blocking `CreateProcessAsUserW`; corporate
policy blocking `CreateRestrictedToken`; error 1385 (the sandbox user lacks *log on locally*);
world-writable directories bypassing the ACL model, which Codex audits and warns about.

**`sandbox-exec` is deprecated and universal.** Codex, Claude Code and srt all use it; Apple offers no
CLI replacement (App Sandbox needs an Xcode-signed app). Every field runtime carries the risk that
Apple removes it. The kit's D36 proof turns that risk into a detector: the day it stops working, the
proof fails closed to `CannotEnforce` rather than a silent `full` (D136).

**Linux: Landlock versus bubblewrap.** Landlock is a kernel LSM a process applies to itself — no
helper binary, no root, no user namespaces; ABI v4 (kernel 6.7) adds TCP `bind`/`connect` control,
v5 (6.10) ioctl scoping; the `landlock` Rust crate probes the kernel for the highest ABI. Bubblewrap
builds a namespace sandbox from outside and needs unprivileged user namespaces, which Ubuntu 24.04's
default AppArmor policy blocks. Codex's order — Landlock first, bwrap fallback — is what D133 adopts;
the kit is bwrap-only today. A bubblewrap escape was published in 2026, which argues for the
in-process mechanism where it exists.

**Process trees** are well-trodden in Rust: `processkit` (tokio; a cgroup v2, a Windows Job Object or
a POSIX process group as a kill-on-drop container), `windows-spawn` (an owned Job object),
`kill_tree`; Cargo itself uses Job Objects on Windows so Ctrl-C ends the tree.

**Windows without elevation cannot isolate the network.** Codex's engineers built the unelevated
model and abandoned it. Phase 43's fork is therefore two models, not three (D134): the elevated model,
or WSL2 as the confined path with native Windows honestly `full`.

## 3. The server side has gone to microVMs

Firecracker boots in ~125 ms with under 5 MiB of overhead (E2B, Vercel Sandbox); gVisor intercepts
syscalls in user space; "a container is not a sandbox" is the 2026 consensus, and Anthropic's own
documentation recommends VM-grade isolation for untrusted repositories. Codex offers Docker
(microVM) sandboxes beside its OS sandbox. This is the cloud's answer — the `OpenSandbox`-class
backend — and not the OS layer's (D137).

## 4. What the grounding changed in the epic

1. **The Rust shrank to helper executables** (D123). macOS needs no native code; Linux needs a small
   helper because Landlock and seccomp are syscalls the child makes on itself; Windows confinement
   needs an elevated executable with its own manifest. A PyO3 extension would add a wheel matrix and
   an ABI coupling the field's designs do without.
2. **Linux goes Landlock first** (D133) — the kit's bwrap-only path is what Ubuntu 24.04 breaks.
3. **Windows' fork is written down** (D134): elevated model or WSL2; no unelevated prototype.
4. **PyApp, embedded** is the named launcher (D127); PyOxidizer excluded by name.
5. **D125 is stricter than Claude Code's default** and equal to its hard mode; said explicitly.
6. **Two seams named for later** (D137): network egress through a proxy with an allowlist; cloud
   microVM confinement. Both are where the field is ahead of the kit.

## 5. Where the kit follows the field, deviates, and lags

| | verdict |
|---|---|
| artifact per platform with the runtime inside; seatbelt; Landlock + seccomp with bwrap fallback; Job Objects; the Windows fork; core-plus-SDKs; microVMs in the cloud | **the field's architecture, layer by layer** |
| the D36 proof before any confined mode opens | **the kit's one addition** — no field runtime proves its sandbox before trusting it |
| fail closed by default | **stricter** than Claude Code's default; equal to its `failIfUnavailable` |
| the engine kept in Python; other languages over a wire rather than an FFI | **choices**, made knowingly (D122, D119) |
| network egress control and credential masking through a proxy | **behind** — D137 |
| Windows | **behind** — closed by Phases 41 and 43 |

## Sources

- Codex: [platform implementation](https://codex.danielvaughan.com/2026/04/08/codex-sandbox-platform-implementation/) · [Windows sandbox internals](https://codex.danielvaughan.com/2026/05/14/codex-cli-windows-sandbox-engineering-restricted-tokens-acls-elevated-architecture/) · [Windows: native sandbox and WSL](https://codex.danielvaughan.com/2026/04/01/codex-cli-windows-native-sandbox-wsl/) · [Ubuntu 24.04 AppArmor fix](https://www.jdhodges.com/blog/codex-sandbox-ubuntu-24-04-fix/) · [coding agent sandboxes, 2026-05](https://gist.github.com/wincent/2752d8d97727577050c043e4ff9e386e)
- Claude Code: [sandboxing docs](https://code.claude.com/docs/en/sandboxing) · [native Windows sandbox request #46740](https://github.com/anthropics/claude-code/issues/46740) · [native build, ~100 MB](https://www.frr.dev/posts/claude-code-native-build-bun/) · [setup](https://code.claude.com/docs/en/setup) · [anthropic-experimental/sandbox-runtime](https://github.com/anthropic-experimental/sandbox-runtime)
- OpenCode: [Windows binary issue #11824](https://github.com/anomalyco/opencode/issues/11824)
- Python distribution: [PyApp](https://ofek.dev/pyapp/latest/) · [PyOxidizer status](https://gregoryszorc.com/docs/pyoxidizer/main/pyoxidizer_status.html) · [shipping a Python application to end users](https://pydevtools.com/handbook/explanation/how-do-i-ship-a-python-application-to-end-users/) · [PyO3 building and distribution](https://pyo3.rs/v0.29.2/building-and-distribution.html) · [maturin distribution](https://www.maturin.rs/distribution.html)
- Core + SDKs: [Why Rust powers Temporal's Core SDK](https://temporal.io/blog/why-rust-powers-core-sdk) · [Temporal sdk-rust ARCHITECTURE](https://github.com/temporalio/sdk-rust/blob/main/ARCHITECTURE.md) · [Tauri sidecar](https://v2.tauri.app/develop/sidecar/)
- Process trees: [processkit](https://crates.io/crates/processkit) · [windows-spawn](https://docs.rs/windows-spawn/latest/windows_spawn/) · [Cargo's Job Objects](https://github.com/rust-lang/cargo/pull/2370)
- Linux: [Landlock kernel documentation](https://docs.kernel.org/userspace-api/landlock.html) · [rust-landlock ABI](https://landlock.io/rust-landlock/landlock/enum.ABI.html) · [bubblewrap](https://github.com/containers/bubblewrap) · [the bubblewrap escape and agent runtime hardening](https://tanayshah.dev/blog/agent-sandbox-runtime-hardening/)
- macOS: [`sandbox-exec` deprecation timeline](https://github.com/apple/containerization/issues/737) · [notarizing a Python macOS app](https://haim.dev/posts/2020-08-08-python-macos-app) · [nested code signing for notarization](https://developer.apple.com/forums/thread/679044)
- Cloud: [sandboxing AI agents in 2026](https://northflank.com/blog/how-to-sandbox-ai-agents) · [microVM isolation in 2026](https://emirb.github.io/blog/microvm-2026/) · [E2B vs Vercel Sandbox](https://vercel.com/kb/guide/vercel-sandbox-vs-e2b)
