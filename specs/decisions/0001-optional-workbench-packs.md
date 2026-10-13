---
type: Decision
---
# 0001 — Optional workbench components reuse engines under generic contracts

> **Status**: accepted
> **Date**: 2026-10-13
> **Deciders**: owner; HDK implementation lane

## Context
The owner extends the 0.48.0 phase to browser and command/workbench primitives. D190 keeps tool vocabulary out of the kernel and new runtime architecture. Products choose component packs; ordinary installation must not launch a browser or require every engine.

A coding tool, a support desk and a research assistant would each use image observations from tools and cleanup of resources allocated to an execution scope. These two generic needs justify additive kernel contracts; browser and test-runner names do not.

## Options considered
- Direct [Playwright Python](https://playwright.dev/python/): Apache-2.0 browser automation, local isolated contexts, accessibility snapshots, screenshots, tabs and network/console hooks. HDK supplies declarations, policy enforcement and lifecycle, rather than another model loop.
- [Playwright MCP](https://github.com/microsoft/playwright-mcp): ready tools and isolated/headless options. Its documentation expressly warns that allowed origins are not a security boundary and do not affect redirects. A transparent wrapper would not prove our required host policy.
- [Browser Use](https://github.com/browser-use/browser-use): MIT local/cloud agent library and CLI. Its agent/model integration and optional personal-profile/cloud features go beyond this pack; adopting the agent loop duplicates HDK's existing loop.
- [Stagehand](https://github.com/browserbase/stagehand): MIT interaction/extraction SDK, with local and hosted integrations. Its model-driven operations would add another inference layer where deterministic engine primitives suffice.

## Decision
Use an optional direct Playwright adapter as the browser engine. Do not expose arbitrary script evaluation, filesystem upload/download or personal/remote browser profiles. Individual operations have declared effects and JSON inputs that provide the existing governance preview. Headless isolated contexts are scoped to a run tree; host-supplied origins default to loopback. Origin denial must be proven against redirects, subresources and sockets, not inferred from navigation validation. Block service workers; keep telemetry and hosted browser services absent.

Add an optional image collection to Completed and Message, defaulting empty, and carry it through checkpoints, model adapters and MCP as image blocks. JSON textual summaries contain only text/data metadata; image bytes are not duplicated into model text.

Add a structural optional run-resource cleanup seam, with a no-resource default. Components in a run tree share an opaque resource scope; cleanup is generic, never branches on a component name, and failures are visible in the run outcome. Old component ports continue to work unchanged. A browser closes at the end of an execution leg (including parking/cancellation); it does not claim that a process survives a durable parked checkpoint.

Reuse the existing environment command driver for direct host access and background jobs. Independent output cursors must not consume the agent's cursor. Background commands are host-owned workspace resources and survive turns until stopped or the owner closes them. Parse standard test reports as data rather than guessing counts from console prose; interactive PTY remains a later extension.

## Consequences
The minor release adds backwards-compatible generic fields and an optional cleanup protocol. Engine dependencies and binaries stay optional/lazy. Browser integration tests need a real binary on CI; installation messages and network restrictions are separately verified. Products keep ownership of origins, permission modes, UI, bridge removal and version pins. This is an explicit owner amendment to the maintenance-only scope; it does not move browser vocabulary into runtime.

## Amendment — 2026-10-13: enforced network boundary and wire compatibility
A real Chromium 1.63.0 test rejected context routing alone: the second hop of a redirect reached a denied origin. A local proxy using the BSD-licensed [proxy.py](https://github.com/abhinavsingh/proxy.py) 2.4.10 engine blocked that same chain, HTTP subresources and a WebSocket CONNECT without request routing. Select a local per-run proxy plugin as the independent origin boundary, with Chromium's implicit loopback bypass disabled. HTTPS/CONNECT, workers, connection reuse, cleanup and protocol escape controls remain acceptance work; this amendment records a tested candidate, not a completed security claim. No TLS interception or personal CA/profile changes are intended.

Empty image collections are omitted from serialized payloads to preserve existing wire data; this uses Pydantic's conditional field exclusion, requiring Pydantic >=2.12. Image-bearing observations remain explicit. Resource scope travels with crossed invocations; cleanup has its own callback and older hosts without that callback keep the no-resource default. Cleanup is an internal runtime method, not an operation an agent can call to stop another execution's resources.
