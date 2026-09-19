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
