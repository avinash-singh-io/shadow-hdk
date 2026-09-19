---
type: History
status: in-progress
---

# phase-44-tools-as-code — History

### [NOTE] 2026-09-19 — Phase 44 brainstormed: the product's order, the kit's principles
Topics: wire, components, inversion, typescript, sidecar, proof
Affects-phases: phase-44-tools-as-code, phase-34-the-harness-as-data
Affects-specs: epics/0009-the-harness-as-data.md#amendments, research/2026-09-19-cross-platform-grounding.md
Detail: A product asked for ENH-030, ENH-031 and BUG-057 first. Each was verified against the code
before it was accepted: the inversion exists on `run`/`resume` (`HostSide`, `RemoteComponents`,
HTTP bidirectional) and not on the thread door; the TypeScript client drives threads only, has the
"runtime asks us" frame path and no stdio transport; the proof misreads 3.13+'s traceback echo,
reproduced with the kit's own `_prove`. Designed generic by the test *would a second, different host
use it unchanged?* — the inversion binds to a connection, not a product (hence host-gone semantics);
the stub is generated from schemas; the transport is a transport; the proof fix is
mechanism-independent. ENH-031's "pinned sidecar" is amended: the pin is Epic 0010 Phase 42's; what
lands is the stub and a stdio transport with a configurable command. Pulling ENH-030/031 ahead of
Phase 34 is a forward-only amendment to Epic 0009, recorded there at Group 4.

---

### [DECISION] 2026-09-19 — P44-1..P44-7 as in overview.md
Topics: wire, components, posture, typescript, proof
Affects-phases: phase-44-tools-as-code
Affects-specs: architecture/wire.md#the-thread-crossed, architecture/adapters.md#the-environment
Detail: `host_components: true` on `thread/start`/`resume` adds a `RemoteComponents` port for the
calling peer (`registered_by = "host:<session>"`, `source: "host"`); a host that goes away takes its
tools with it by name; a remote irreversible act is `observed` (Phase 33's rule); the TS client gains
a stdio transport and a host-side `ComponentPort`; the proof reads stdout and the exit code only.
Protocol stays 3. [ARCH_CHANGE] pending for `/sync-docs`: the thread, crossed, gains the host's
components; the environment's proof reads stdout.

---

### [DISCOVERY] 2026-09-19 — BUG-058: a union compared by identity, which 3.14 no longer guarantees
Topics: tests, python-3.14, kernel
Affects-phases: phase-44-tools-as-code
Affects-specs: none
Detail: With BUG-057 fixed, the whole suite on 3.14.6 left one non-TS failure: the adapter-cache
test counted constructions with `what is wanted`, and on 3.14 `Event | None` evaluated twice is two
equal union objects with one hash (3.12 returned the same object). The cache held — it is keyed by
the type — only the test's comparison was wrong. Fixed inline (equality), filed closed.

---

### [NOTE] 2026-09-19 — G1: the proof reads stdout and the exit code
Topics: proof, environment, python-3.14
Affects-phases: phase-44-tools-as-code
Affects-specs: architecture/adapters.md#the-environment
Detail: `_prove.attempt(script, marker)` answers *did the probe say the marker on stdout with a
zero exit* — a traceback is stderr, and 3.13+ echoes the `-c` source in it, marker included. Green
on 3.12 (69) and 3.14 (the 25 that failed yesterday pass; the full suite 1,774 passed with only this
phase's own RED left). The rule is mechanism-independent and is what Epic 0010's helpers will be
held to. [ARCH_CHANGE] pending for `/sync-docs`: the environment's proof reads stdout only.

---
