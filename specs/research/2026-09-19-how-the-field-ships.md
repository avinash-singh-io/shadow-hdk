---
type: Research
status: complete
date: 2026-09-19
epic: cross-platform
---

# How the field ships — the distribution mechanisms, and where the kit stands against them

> A wide, shallow survey done 2026-09-19 before committing the release order, so that "the
> artifact" and "the sidecar" were understood as two of several mechanisms rather than the only
> two. Companion to `2026-09-19-cross-platform-grounding.md`, which is about confinement per OS.
> Sources at the end.

## The mechanisms

| # | mechanism | what is on the user's machine | who supplies the runtime | who does it |
|---|---|---|---|---|
| **A** | **a library in the consumer's process** | the product's app, the kit one dependency inside it | the product's installer | every SDK — LangGraph, the OpenAI Agents SDK, Temporal (whose Rust core rides *inside* the host process via FFI: "deploy one binary") |
| **B** | **a zero-install runner** | nothing until first run; a launcher fetches the tool | `uvx` · `pipx` · `npx` · `bunx` | how most MCP servers are run (`npx -y …`, `uvx …`); `langgraph dev` |
| **C** | **a sidecar the app spawns** — a second program over stdio or loopback | the app plus one executable beside it | one of C1–C3 | Tauri sidecars; VS Code language servers; Claude Code bundling ripgrep; Electron + a PyInstaller'd Python backend; the Ollama app spawning its own server |
| C1 | · bundled in the installer, per platform | the executable shipped inside the app | the executable carries its runtime | Tauri (`binary-$TARGET_TRIPLE`); VSIX-per-platform extensions; Electron + PyInstaller one-file |
| C2 | · downloaded on first run | a stub; the binary arrives on first launch | a download step | PyApp's default; several language-server extensions |
| C3 | · **the host ships the runtimes once; bundles declare what they need** | the host carries Node and `uv`; each server declares `node` / `python` / `uv` / `binary` | **the host app** | **Claude Desktop + MCPB** — "users don't need to install any runtimes … the host manages Python and dependencies automatically" |
| **D** | **a local daemon with a local API** — one background process per machine, shared | a service (launchd · systemd · a Windows service) | itself | Ollama's server; Docker Desktop's backend; Tailscale's `tailscaled` LocalAPI |
| **E** | **a container / self-hosted server** | an image | the image | LangGraph Platform self-hosted; Ollama's official image; Temporal workers |
| **F** | **a hosted runtime** | nothing; the product's backend calls a service | the vendor | LangGraph Cloud; Temporal Cloud; OpenAI's hosted sandboxes |
| **G** | **a bundle with a manifest** — a portable package a host knows how to run | a zip with `manifest.json` | the host, per the manifest | **MCPB** (`.mcpb`); VSIX; browser extensions |
| **H** | **Wasm components** — portable, sandboxed plugin code in any language | `.wasm` files the host loads | the host's wasm runtime (wasmtime · Extism) | plugin systems (moonrepo, Dylibso); "the runtime for plugin systems" in 2026 |

## Three findings

1. **There is a third answer to "who carries the interpreter", and the most-installed desktop AI
   app chose it.** Claude Desktop does not ask each extension to bring Python; it ships `uv` and
   Node *once*, and a bundle declares `server.type = "uv"`. For a host app that means a cheap path
   even in the sidecar shape: **ship `uv` (a ~15 MB static binary) in the installer and run the kit
   through it** — no per-OS kit artifact needed, at the cost of a first-run interpreter fetch
   (PyApp's default does the same). Phase 42's binary is thereby reframed: required for a sidecar
   *without network on first run*, not for a sidecar as such.
2. **A bundle with a manifest is how the field ships "a thing a host runs."** MCPB is the shape
   Phase 34's harness bundle wants — a zip, a manifest declaring runtime requirements, the host
   supplying the runtime. Phase 34 aligns with MCPB's conventions rather than inventing a format,
   and the kit can *consume* `.mcpb` bundles as batteries (a battery is an MCP server; MCPB is its
   portable packaging) — ENH-033.
3. **The daemon shape is a deployment choice, not a kit feature.** `shadow-hdk serve --http` is
   already a daemon with a bearer; registering it as an OS service is the installer's job, as it is
   for Ollama and Tailscale. The field's named risk — an unauthenticated loopback port — the kit
   already answers.

**Wasm** is the one genuinely new idea: a `ComponentPort` adapter that loads a `.wasm` component
gives a tool that is cross-OS *and* sandboxed by construction, in any language — ENH-034, later.

## Where the kit stands

| mechanism | the kit today | planned | note |
|---|---|---|---|
| A in-process | ✓ `pip install shadow-hdk`; `Harness` · `Thread` · `run()` | — | the shape a product that runs the kit in its own process uses |
| B zero-install | ✓ `uvx --from shadow-hdk shadow-hdk serve` | — | needs `uv`; a developer's channel |
| C sidecar over stdio | ✓ `spawnHarness` (0.32), with B underneath | C1 = Phase 42, when a no-network first run is required | the host-ships-`uv` form of C3 is available to any installer now |
| D daemon | ✓ `serve --http` with a bearer | — | service registration is the installer's |
| E container | works; no official image | Epic 0010 | small |
| F hosted | — | **non-goal** | a kit, not a service |
| G bundle + manifest | — | **Phase 34**, aligned with MCPB; `.mcpb` as batteries (ENH-033) | |
| H wasm components | — | candidate (ENH-034) | |

## What it changed

Almost nothing in the architecture, which is the point of checking. The blocker list for a
macOS + Linux laptop release stays at two — BUG-056 and Linux confinement on Ubuntu 24.04 — and the
per-OS artifact stays optional: a product running the kit in-process needs none, and a sidecar has
the ship-`uv` path today. Epic 0010's order is amended accordingly (its Amendments section).

## Sources

- MCPB: [Build a desktop extension with MCPB](https://claude.com/docs/connectors/building/mcpb) · [modelcontextprotocol/mcpb](https://github.com/modelcontextprotocol/mcpb) · [Anthropic engineering: desktop extensions](https://www.anthropic.com/engineering/desktop-extensions) · [Azure MCP as .mcpb](https://devblogs.microsoft.com/azure-sdk/azure-mcp-server-mcpb-support/)
- Daemons: [Ollama desktop app architecture](https://deepwiki.com/ollama/ollama/8.1-desktop-app-architecture) · [Docker Desktop networking backend](https://docs.docker.com/desktop/features/networking/) · [tailscaled daemon and LocalAPI](https://deepwiki.com/tailscale/tailscale/5.1-tailscaled-daemon-architecture) · [the daemon pattern's risks on endpoints](https://medium.com/@michael.hannecke/sovereign-ai-on-the-endpoint-where-the-daemon-pattern-breaks-down-in-regulated-environments-f421e5ac632b)
- Sidecars: [VS Code language server guide](https://code.visualstudio.com/api/language-extensions/language-server-extension-guide) · [bundling a language server per platform](https://github.com/hashicorp/vscode-terraform/issues/820) · [Tauri sidecar](https://v2.tauri.app/develop/sidecar/) · [bundling Python inside Electron](https://til.simonwillison.net/electron/python-inside-electron)
- Frameworks: [LangGraph Platform GA](https://www.langchain.com/blog/langgraph-platform-ga) · [self-hosting a LangGraph server](https://docs.langchain.com/langsmith/deploy-standalone-server) · [Temporal workers](https://docs.temporal.io/workers) · [OpenAI Agents SDK, the next evolution](https://openai.com/index/the-next-evolution-of-the-agents-sdk/)
- Wasm: [Extism](https://github.com/extism/extism) · [WASI and the component model, status](https://eunomia.dev/blog/2025/02/16/wasi-and-the-webassembly-component-model-current-status/)
