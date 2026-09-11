---
type: Phase
phase: 22
name: the-environment
epic: 0011-the-environment
status: complete
topics: [environment, mode, confinement, seatbelt, bubblewrap, opensandbox, d36, bug-018]
deps: [phase-21-the-visible-agent]
---

# Phase 22 — The environment

Three adapters each held an opinion about the same boundary. `workspace` confined file operations
by checking every path. `sandbox_subprocess` ran commands with a leash and no boundary at all.
`contained` proved isolation for a third kind of execution. A mode permitting workspace writes was
told three different truths about what a write reaches, and BUG-018 was the one that was false.

Every mature agent runtime has the same answer, and it is not three tools. It is **one environment
with a mode**, enforced once by the environment, true for every operation in it:

* **Codex**: `read-only`, `workspace-write`, `danger-full-access` — enforced by the OS sandbox
  around the whole process (seatbelt on macOS, Landlock on Linux). Its file tools and its shell
  tool are ordinary; the environment is what is confined.
* **Claude Code**: works in `cwd`; widening is a permission question a person answers.
* **TrueForge**: files and commands happen *inside* the sandbox; the harness holds the secrets.

## What this phase makes true

**An environment is where effects land, and it has a mode.** `read-only` · `workspace-write` ·
`full`. The effect profile of every operation in it — read, write, list, run — is derived **once**
from the environment's isolation, its mode and the operation, and it is true because the
environment makes it true. BUG-018's class is closed by shape, not only by the invariant that
caught it.

**A mode is enforced or refused.** A `LocalEnvironment` asked for `workspace-write` on a machine
with no OS sandbox does not quietly widen; it refuses to exist, naming what is missing (D25's
rule, applied to a mode). `full` always works and declares everything. A host that asked for
confinement and cannot have it must know, not find out.

**Local execution is confined for real.** `sandbox-exec` on macOS — measured 2026-09-11: a write
outside the root is *Operation not permitted*, a socket is denied, the interpreter runs.
Bubblewrap on Linux where present. Proven at construction by what is denied (D36), never by what
the wrapper announces.

**Isolated execution is consumed, not built.** `SandboxEnvironment` sits behind the existing
`IsolationBackend` seam; the first backend is OpenSandbox — Docker on a laptop, gVisor, Kata or
Firecracker on a cluster, a Python SDK, CNCF-listed — with the root mounted in. The hand-rolled
gVisor and Firecracker wrappers are deleted. `prove()` grows a second denial: a write outside the
root, not only a socket, because that is the boundary BUG-018 was about.

**Root defaults to where the harness was launched**, and **widening is an `Ask`** — *may I read
elsewhere?* is a question a person answers, not a tool the agent has.

## What is deliberately not here

A browser environment (Phase 25 territory — Playwright MCP is an MCP server and arrives as a
component). Memory. Anything coding-specific: an environment is a filesystem and a shell for one
agent and the physical world for another (D29); the mode is the same word for both.

## The survey, recorded (principle 5)

Local OS sandboxes: `sandbox-exec` (macOS, built in, deprecated by Apple and still functional in
macOS 26 — measured), bubblewrap (Linux, what Flatpak uses), Landlock (Linux kernel ≥ 5.13, what
Codex uses natively; needs a Python binding or ctypes — deferred). Isolated: OpenSandbox 0.1.16
(chosen: self-hosts with Docker, four isolation runtimes, MCP server, Python SDK, Apache-2, CNCF),
E2B 2.49.1 and Daytona 0.211.2 (the same seam, a file plus one adapter each), CubeSandbox (KVM,
Linux-only, E2B-compatible API — reachable through the E2B adapter when it exists).
