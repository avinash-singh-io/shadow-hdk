---
type: Impact Map
title: Decision Impact Map
description: "Topic keywords → spec files/sections, consumed by /sync-docs."
---

# Impact Map

Maps topic keywords to the spec files/sections they affect. Used by
`/sync-docs` to find documents needing updates when a phase history
entry carries matching `Topics:`.

| Topic | File | Section |
|-------|------|---------|
| runtime, resume, leases | specs/architecture/runtime.md | The drive; The governed step |
| wire | specs/architecture/wire.md | Rules already fixed |
| agent, transcript | specs/architecture/adapters.md | The agent adapter |
| sandbox, workspace | specs/architecture/adapters.md | The workspace and code adapters |
| mypy, ci, landing | specs/architecture/testing.md | Layers |
| spec-drift | specs/architecture/file-structure.md | (whole file) |
| posture | specs/epics/0007-the-environment.md | Decisions |
| mqtt | specs/architecture/adapters.md | The map |
| devices | specs/architecture/adapters.md | The map |
| d32 | specs/epics/0007-the-environment.md | Decisions |
| envelope | specs/phases/phase-16-mqtt/design.md | 3.1 The envelope |
| link | specs/phases/phase-16-mqtt/design.md | 3.2 The link as a state machine |
