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
| sandbox, environment, workspace, roots | specs/architecture/adapters.md | The environment — where the agent's effects land |
| modes, approval, ask | specs/architecture/adapters.md | The modes adapter — what ships now |
| thread, turn, item, activity, store, registries, tools, skills | specs/architecture/wire.md | The thread, crossed |
| processes, framing, one-implementation | specs/architecture/runtime.md | Modules |
| providers, claude-code, codex, resume, clean-scope | packages/providers/src/shadow_hdk/providers/library/ | the provider files |
| serve, facade, batteries, keeping | specs/architecture/adapters.md | Batteries; specs/architecture/overview.md — the front door |
| shadow, hdk, harness, progressive-control, blueprint, preset | specs/vision/project-charter.md; specs/planning/roadmap.md | Solution; Vision; Guiding Principles |
| capabilities, requirements, provider-evidence, compatibility | specs/architecture/adapters.md; specs/architecture/wire.md | Providers; The thread, crossed |
| authority, revisions, effect-authorization, act-time | specs/architecture/runtime.md | The governed step; Acting |
| effect-journal, reconciliation, unknown-outcome, receipts | specs/architecture/runtime.md; specs/architecture/wire.md | Acting; The record |
| model-agent, agent-surface, item-inputs, stream-session, heartbeat, authentication, typescript | specs/architecture/adapters.md; specs/architecture/runtime.md; specs/architecture/wire.md; specs/architecture/testing.md | The agent adapter; Modules; The thread, crossed; Cases |
| dynamic-planning, scheduling, generative-ui, collaboration, evolution | specs/planning/roadmap.md | Timeline; What comes next; Guiding Principles |
| mypy, ci, landing | specs/architecture/testing.md | Layers |
| spec-drift | specs/architecture/file-structure.md | (whole file) |
| posture | specs/epics/0007-the-environment.md | Decisions |
| mqtt | specs/architecture/adapters.md | The map |
| devices | specs/architecture/adapters.md | The map |
| d32 | specs/epics/0007-the-environment.md | Decisions |
| envelope | specs/phases/phase-16-mqtt/design.md | 3.1 The envelope |
| link | specs/phases/phase-16-mqtt/design.md | 3.2 The link as a state machine |
