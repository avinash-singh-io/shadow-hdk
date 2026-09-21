---
type: Research
status: complete
date: 2026-09-21
---

# Shadow and Goose — architectural grounding

This is documentation and selected-source research, **not a benchmark, executable compatibility
proof or security audit**. Goose source observations use commit
`aa6916a226391f5a1a7836974d3726ecb98c6425`; documentation was reviewed on 2026-09-21. Shadow's
native architecture is a target, not a shipped comparison baseline.

| Area | Grounded Goose observation | Consequence for Shadow |
|---|---|---|
| Agent construction | `goose-agent` exposes operations, inference, a state machine and runtime-provided persistence traits over conversation state [1] | Do not describe Goose as only an app or claim that construction kits are unique to Shadow |
| Maturity boundary | The inspected application integration is opt-in through `GOOSE_STATE_MACHINE`; concrete built-in operations remain internal [2] | Public availability and stable reuse must be checked per piece |
| SDKs | The documented alpha native SDK exposes providers; Python/Kotlin bindings come from Rust. Full-agent clients use ACP [3,4] | Specify native bindings, runtime clients and authoring helpers separately |
| TypeScript | The ACP client has types/validators and extension helpers, but does not install or start the executable [5] | Managed lifecycle is an explicit SDK responsibility if Shadow promises it |
| Recipes | Parameters, extensions, model settings and output validation exist; documented subrecipes run in separate sessions and cannot themselves define subrecipes [6,7] | Convenient definitions are expected; explicit bounded nested composition is a concrete requirement, not a claim that all Goose composition is impossible |
| Policy hooks | Tool blocking and failure policy exist; `PreToolUseResult` delivery is best-effort and non-durable [8] | Observation hooks are not a durable effect journal or an authorization lease |
| Applications | Goose Desktop uses ACP/WebSocket to its local server [4] | First-party Shadow surfaces should consume public interfaces |
| Performance | No equivalent-workload measurement performed in this review | Native implementation alone proves no RAM/CPU advantage |

## Decision implications

Keep a pure contract layer, a shared execution runtime and replaceable strategies. Do not force
every workflow into a chat transcript, or implement a different execution engine in each SDK.
Consume suitable libraries behind ports. Evaluate Goose agent/provider pieces with a bounded
proof, including governance-before-effect, cancellation, persistence ownership, dependency weight
and API stability. Do not select a whole Goose application as Shadow's mandatory foundation from
feature lists alone, and do not build duplicates merely to avoid using dependencies.

Current Shadow already has explicit composition and plan admission, effect authority/journaling,
Python execution and a TypeScript wire/client tool surface. Its byte-oriented `RunStore` plus
LangGraph checkpoint serialization is not yet the proposed canonical native execution journal.
The migration must account for all supported behavior, not only the small scheduler import count.

## Sources

1. [Agent library](https://github.com/aaif-goose/goose/blob/aa6916a226391f5a1a7836974d3726ecb98c6425/crates/goose-agent/README.md)
2. [Application state-machine integration](https://github.com/aaif-goose/goose/blob/aa6916a226391f5a1a7836974d3726ecb98c6425/crates/goose/src/agents/state_machine/mod.rs)
3. [Native SDK](https://goose-docs.ai/docs/gdk/sdk/)
4. [ACP and Desktop integration](https://goose-docs.ai/docs/gdk/acp/)
5. [TypeScript ACP client](https://github.com/aaif-goose/goose/blob/aa6916a226391f5a1a7836974d3726ecb98c6425/ui/goose-acp-client/README.md)
6. [Recipe reference](https://goose-docs.ai/docs/guides/recipes/recipe-reference/)
7. [Subrecipes](https://goose-docs.ai/docs/guides/recipes/subrecipes/)
8. [Hooks](https://goose-docs.ai/docs/guides/context-engineering/hooks/)
