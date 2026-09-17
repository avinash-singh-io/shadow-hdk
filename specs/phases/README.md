---
type: Guide
---

# Phases Index

| Phase | Name | Status | Directory |
|-------|------|--------|-----------|
| 0 | The runtime | Complete | `phase-0-the-runtime` |
| 1 | Real adapters | Complete | `phase-1-real-adapters` |
| 2 | The spike | Complete | `phase-2-the-spike` |
| 3 | Workspace and code | Complete | `phase-3-workspace-and-code` |
| 4 | The ACP bridge | Complete | `phase-4-the-acp-bridge` |
| 5 | The RecordingServer | Complete | `phase-5-the-recording-server` |
| 6 | The compiler complete | Complete | `phase-6-the-compiler-complete` |
| 7 | Sub-agents | Complete | `phase-7-sub-agents` |
| 8 | Patterns, skills and replay | Complete | `phase-8-patterns-skills-replay` |
| 9 | The wire | Complete | `phase-9-the-wire` |
| 10 | Effect rules | Complete | `phase-10-effect-rules` |
| 11 | Contained sandboxes | Complete | `phase-11-contained-sandboxes` |
| 12 | Derivation | Complete | `phase-12-derivation` |
| 13 | Effect leases | Complete | `phase-13-effect-leases` |
| 14 | Telemetry | Complete | `phase-14-telemetry` |
| 15 | Environment contract | Complete | `phase-15-environment-contract` |
| 16 | MQTT | Complete | `phase-16-mqtt` |
| 17 | The audit | Complete | `phase-17-the-audit` |
| 18 | The P1s | Complete | `phase-18-the-p1s` |
| 19 | The P2s | Complete | `phase-19-the-p2s` |
| 20 | Providers | Complete | `phase-20-providers` |
| 21 | The visible agent | Complete | `phase-21-the-visible-agent` |
| 22 | The environment | Complete | `phase-22-the-environment` |
| 23 | A host in any language | Complete | `phase-23-a-host-in-any-language` |
| 24 | The skill registry | Complete | `phase-24-the-skill-registry` |
| 25 | The host's controls | Complete | `phase-25-the-hosts-controls` |
| 26 | Any language | Complete | `phase-26-any-language` |
| 27 | Batteries and the facade | Complete | `phase-27-batteries-and-the-facade` |
| 28 | The workspace | Complete | `phase-28-the-workspace` |
| 29 | One app server behind every surface | Complete | `phase-29-one-app-server` |
| 30 | A product owns what it owns | Complete | `phase-30-a-product-owns-what-it-owns` |
| **31** | **A host knows what it can trust** | **Complete, v0.30.0 release** | `phase-31-a-host-knows-what-it-can-trust` |
| **32** | **One agent surface** | **Complete, v0.30.0 release** | `phase-32-one-agent-surface` |
| **33** | **Authority at the act** | **Complete, v0.30.0 release** | `phase-33-authority-at-the-act` |
| **36** | **Plan admission** | **In Progress — Epic 0009** | `phase-36-plan-admission` |

## Phase Structure

Each phase directory contains:

| File | Purpose |
|------|---------|
| `overview.md` | Goal, scope, deliverables, acceptance criteria |
| `plan.md` | Group execution pattern with tasks |
| `tasks.md` | Checklist `[ ]` / `[x]` |
| `history.md` | Append-only log |
| `retrospective.md` | Post-completion review (created by /complete-phase) |

## Swarm-member briefs (optional)

When a phase is driven by a swarm conductor (Phase 17+), `overview.md`
MAY carry an optional YAML frontmatter block declaring its swarm
context. Solo briefs omit this entirely — they remain plain markdown.

```yaml
---
swarm: 0007-user-auth
wave: 2
initiative: user-auth
claimed_by_session: <session-uuid>
---
```

`/start-phase` populates these when invoked from a swarm context.
`/validate` checks that `swarm:` resolves to a real swarm manifest,
that `wave:` matches the wave the swarm has assigned this repo, and
that `initiative:` matches the swarm's initiative.
