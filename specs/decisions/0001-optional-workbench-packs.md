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

Add a structural optional run-resource cleanup seam, with a no-resource default. Components in a run tree share an opaque resource scope; cleanup is generic, never branches on a component name, and failures are visible in the run outcome. Old component ports continue to work unchanged. A low-level root retains resources while parked and releases them when it ends. A host may supply `RunOptions.resource_scope` and own teardown itself; Conversation/Thread use their identity across turns and approval settlement, releasing the scope on close. Ports allocating resources in a host-owned scope are the host's responsibility, including any additional ports introduced by child compositions. A browser context survives turns and approval pauses while its host remains alive; a durable checkpoint cannot preserve a browser process across host restart.

Reuse the existing environment command driver for direct host access and background jobs. Independent output cursors must not consume the agent's cursor. Background commands are host-owned workspace resources and survive turns until stopped or the owner closes them. Parse standard test reports as data rather than guessing counts from console prose; interactive PTY remains a later extension.

## Consequences
The minor release adds backwards-compatible generic fields and an optional cleanup protocol. Engine dependencies and binaries stay optional/lazy. Browser integration tests need a real binary on CI; installation messages and network restrictions are separately verified. Products keep ownership of origins, permission modes, UI, bridge removal and version pins. This is an explicit owner amendment to the maintenance-only scope; it does not move browser vocabulary into runtime.

## Amendment — 2026-10-13: enforced network boundary and wire compatibility
A real Chromium 1.63.0 test rejected context routing alone: the second hop of a redirect reached a denied origin. A local proxy using the BSD-licensed [proxy.py](https://github.com/abhinavsingh/proxy.py) 2.4.10 engine blocked that same chain, HTTP subresources and a WebSocket CONNECT without request routing. Select a local per-run proxy plugin as the independent origin boundary, with Chromium's implicit loopback bypass disabled. HTTPS/CONNECT, workers, connection reuse, cleanup and protocol escape controls remain acceptance work; this amendment records a tested candidate, not a completed security claim. No TLS interception or personal CA/profile changes are intended.

Empty image collections are omitted from serialized payloads to preserve existing wire data; this uses Pydantic's conditional field exclusion, requiring Pydantic >=2.12. Image-bearing observations remain explicit. Resource scope travels with crossed invocations; cleanup has its own callback and older hosts without that callback keep the no-resource default. Cleanup is an internal runtime method, not an operation an agent can call to stop another execution's resources.

## Amendment — 2026-10-13: lifetime follows the owner, not an execution leg
New failing controls showed that execution-leg cleanup destroyed resources before a parked approval resumed and between conversation turns. Host-owned resource scopes now cross both run and resume; children inherit the scope. Conversation and Thread settle teardown before propagating caller cancellation, deduplicate aliases, attempt all resource ports after an error and report cleanup failures. Thread also releases its store hold on cleanup failure and repeated cancellation (BUG-241). This corrects the earlier execution-leg decision before a browser implementation relies on it. Resources are process-local, not serialized browser profiles; closing a host scope deliberately invalidates them even if a durable question remains pending.

## Amendment — 2026-10-13: inspect the scheme before any upstream connection
The plain CONNECT candidate cannot distinguish an approved HTTP origin from a denied HTTPS origin on the same authority. Replace it with the MIT-licensed [mitmproxy](https://docs.mitmproxy.org/stable/) 12.2.3 local engine. Lazy upstream connections and disabled upstream certificate sniffing let the policy inspect each decrypted request before contacting its origin, including redirects and WebSockets. Chromium trusts only the private profile's ephemeral CA public-key hash; the host's system trust and personal browser are untouched. Upstream certificate verification remains enabled. Real controls prove approved TLS works with an explicit test CA, untrusted upstream TLS returns a visible 502 without an HTTP request, and denied HTTP/TLS servers receive neither requests nor TCP connections. A positive STUN control establishes that the governed Chromium's non-proxied UDP restriction is effective. Browser CI exercises Linux 3.12 and macOS 3.14. These controls are release gates, not an OS-wide network sandbox claim.

mitmproxy's pinned dependencies conflict with the kernel's Pydantic 2.12 requirement on Python 3.12. Keep both upstream contracts: the optional browser extra includes Playwright and uv; uv provisions a separate interpreter environment for the pinned gateway SDK on first use, then HDK owns that SDK process directly. Its code resource is packaged with HDK and imports no HDK runtime inside the SDK. Ordinary installation and catalogue construction launch nothing. SDK/browser provisioning may download engine assets; page traffic thereafter passes through the local gateway. Activities report first-use preparation and Chromium installation. Browser images travel as native image blocks; the LangChain chat projection places the image carrier after the entire text tool-result batch, preserving tool-call associations and native chat protocol ordering.

## Amendment — 2026-10-13: negotiate teardown and separate SDK bootstrap discovery
The initialize request advertises `run_resources: true` for hosts implementing resource teardown. Runtime callbacks are sent only after that explicit advertisement. Older hosts retain the no-resource default without a speculative callback: legacy clients report unknown methods with inconsistent codes. Advertised cleanup failures propagate; error-code guessing must not hide a real owner's failure. TypeScript tools receive the scope and can supply an optional cleanup function; aliased functions release once and all owners are attempted after an error. Raw component owners supply `onReleaseRun`.

`Dialect.private_working_directory`, default false, separates a tool-injected CLI SDK's startup directory from the host data its offered tools govern. A coding tool, a support desk and a research assistant may each need this property. The private directory persists across process-per-turn resumes, is removed when the session closes, and never changes the component environment's roots. Codex explicitly disables native world tools and automatic instructions, but its project skill discovery survives those switches; a real local model-endpoint probe demonstrated that path. Private startup prevents it reading the governed repository during discovery. This is an additive generic contract in 0.48.0, not process confinement or a replacement for the host's OS environment policy. Uninjected CLI use keeps its supplied directory and provider defaults. Unsupported SDK switches fail visibly; no fallback enables native tools.

## Amendment — 2026-10-13: restrict SDK model catalogues before launch
A recognized Codex model still receives native patching and deferred tool discovery despite the explicit switches; the earlier unknown-model control did not exercise that metadata. Release is blocked until recognized, code-mode and unknown-model catalogues are checked. A real local endpoint spike proves a restricted catalogue disables both paths without losing the offered MCP tools.

Add optional `Dialect.launch_catalogue` data, default absent: a probe argument vector, a literal top-level list key, literal scalar field replacements, a config argument/template and environment keys isolated for that probe. A coding tool, a support desk and a research assistant may each need to narrow an SDK's own model/tool catalogue before opening governed ports. There are no expressions, vendor branches or tool names in the runtime. The JSONL adapter reads the SDK's bundled metadata in an owned directory, bounds output and time, refuses malformed or unsupported probes, writes an owned catalogue and keeps it across resumes until close. All unspecified metadata stays intact. The real launch keeps the original authentication environment. Uninjected sessions run no probe and use normal defaults; no error enables permissive retry.

Catalogue fields are required by default; `require_present=false` explicitly allows inserting an optional metadata field. Code-mode-only models need direct tool mode and the normal Responses shape because the governed SDK disables its native REPL. The provider pins those launch facts as data, without changing model prompts, capacities or authentication.

## Reopened — 2026-10-13: browser interaction and observation engine
Before release acceptance, the owner requests pinned comparisons of Vercel agent-browser, Browser Use's direct browser layer and Browserbase Browse CLI against the Playwright implementation. Prefer agent-browser if the behavioral controls pass and it reduces custom observation/reference maintenance. HDK retains declarations, previews, approvals, audit, exact origin enforcement and resource ownership. Preserve the current adapter until the selected engine passes; compare local isolated operation, licenses, cloud boundaries, capability coverage, resource use and limitations, and extend public element-reference arguments as warranted. No new owner approval is needed to choose or implement.

Recognized code-mode metadata also advertises experimental tools and a separate second-generation agent facility. Literal replacements may contain immutable string lists as well as scalars; the governed provider clears experimental offerings and resets its agent-generation metadata. The catalogue control checks the exact nested tools, not merely absence of shell.


## Selection checkpoint — 2026-10-13: agent-browser preferred, replacement not accepted
The owner delegated engine choice without further approval, then stopped implementation/release.
Select **agent-browser 0.39.0 as the preferred replacement candidate**: it supplies native
accessibility observations and reusable element references without another model loop, and has
the smallest observed interaction-daemon footprint in this fixture. This choice does not accept
its incomplete adapter. **Keep Playwright as the operational default** until all replacement
behavioral gates pass. The original decision above describes the preserved implementation;
this amendment records the reopened comparison and its current status.

| Pinned engine | License and primary evidence | Local/isolated evaluation and boundary | Result/limits |
|---|---|---|---|
| Playwright Python 1.63.0 | Apache-2.0; [source tag](https://github.com/microsoft/playwright-python/tree/v1.63.0) | Local private Chromium, HDK-owned gateway and profile, deterministic primitives | Existing full browser controls and mutations pass; lacks agent reference map, requiring custom HDK observation/reference work |
| Vercel agent-browser 0.39.0 | Apache-2.0; [release/source](https://github.com/vercel-labs/agent-browser/releases/tag/v0.39.0) | Native Rust daemon attached only to HDK-created local CDP endpoint; private HOME/socket/session, sanitized environment; pinned lazy binary | Local navigation, reference fill/click, snapshots, PNG and tabs demonstrated; selected candidate full real gate fails three cases, so not accepted |
| Browser Use 0.13.11 | MIT; [source tag](https://github.com/browser-use/browser-use/tree/0.13.11), commit 914c59bdd4acd50e9628a97a96a3919313aebc85 | Direct BrowserSession/actor/DOM layer with owned local CDP, private configuration/profile, telemetry and default extensions disabled; no Agent/LLM loop | Local fill/click, DOM references and screenshots pass; viable direct-layer alternative, larger Python dependency/runtime footprint; no complete HDK origin/lifecycle gate claimed |
| Browserbase Browse 0.11.1 (unscoped `browse`) | MIT packaged LICENSE; [npm release](https://www.npmjs.com/package/browse/v/0.11.1), [Stagehand source](https://github.com/browserbase/stagehand) | Explicit foreground managed-local/headless target with private HOME/daemon directory, sanitized no-key environment and local Chromium | Local interaction/snapshot/PNG and 35 XPath references pass. Attaching to common Chromium timed out; cause unconfirmed. Deprecated scoped @browserbasehq/browse-cli 0.6.1 was evaluated first, then superseded, not selected |

No candidate adopts a second agent loop. Agent-browser optional cloud providers, credentials,
auth vault, plugins/WebMCP and personal-profile/auto-connect features are not enabled. Browser
Use cloud/account/agent services are outside the direct layer tested here. Browse managed-local
commands need no cloud account; cloud/platform Fetch/Search and hosted sessions are outside the
selected feature boundary. Browse's potentially sensitive diagnostic network capture is not a
requirement to enable. All page traffic must remain behind HDK's local exact-origin gateway;
provisioning downloads are separately announced. Browser/proxy assets retain their licenses.

### Comparative fixture measurements
Raw results and original experiment scripts are committed under
`specs/phases/phase-67-workbench-corrections/evidence/browser-engine-comparison/`.
The small local form fixture uses private headless Chromium; ten warm snapshots are measured.

| Engine | Warm snapshot median | Observation bytes / references | Auxiliary process RSS |
|---|---:|---:|---:|
| Playwright | 2.160 ms | 151 / no generated references | Not measured separately |
| agent-browser | 1.086 ms | 302 / 6 | 13.0 MB daemon RSS |
| Browser Use direct layer | 7.196 ms | 284 / 4 | 100.4 MB peak Python process RSS |
| Browse managed-local | 4.987 ms | 354 / 35 | 147.0 MB daemon RSS |

Agent-browser daemon CPU for ten snapshots: 0.002821 s; Browse: 0.026126 s. Browser Use's
0.416840 s CPU covers the whole process, so it is not a comparable ten-snapshot figure.
Agent-browser startup+interaction was 0.124 s and Browse managed-local 1.124 s in these runs.
These measurements exclude Chromium, HDK, proxy and some startup ownership costs; peak Python
RSS and live daemon RSS are different scopes. They are not energy measurements, universal
performance rankings or representative measurements on large production pages. All tested
pins have permissive licenses; capability/control acceptance decides the final integration.

### Preserved candidate implementation and remaining gates
HDK retains tool declarations, previews, approvals, audit, exact scheme/host/port policy and
resource lifetime. `AgentBrowserEngine` reuses native SDK interaction and reference observations;
public target arguments accept `ref` (`@eN`) mutually exclusively with selector/role. Role/name
resolution uses the SDK reference catalogue. No custom JavaScript reference insertion is used.
HDK still uses owned Playwright Chromium/gateway startup and per-tab HTTP status/console/network
association. SDK log observations omit tab identity; tabs and indexed-CSS compatibility still
need this glue. This reduces custom reference/observation code, not all browser integration code.
Lazy native assets use pinned archive/per-platform binary digests, bounded extraction and an
owned cancellable installer; new integrity/bounds/concurrency/cancellation mutation proof is
unfinished. The npm wrapper requires Node >=24, while the selected native binary needs no Node.
Platform pins beyond the current macOS run are not behaviorally accepted by this comparison.

Two focused real reference/image/cleanup controls pass. The broader combined browser run
completed before stop: **15 passed, 3 failed**, exit 1, in 159.35 s. All failures are on the
agent-browser candidate: an HTTP error page returns `ERR_HTTP_RESPONSE_CODE_FAILURE` instead
of the expected HTTP-status observation, and two `#done:text-is('Finished')` waits fail. Those
waits precede final UDP/subresource assertions; do not infer the candidate passed those boundaries.
Full controls for references, waits, HTTP errors, origins, images, lifecycle, wire delivery,
installation and mutations must pass before default replacement. Do not fix or rerun them while
paused. The complete earlier Playwright adapter and evidence remain intact.

### Codex verification preserved, not accepted
The launch-catalogue candidate now preserves required metadata, explicitly clears experimental
and agent-generation entries, restricts code-mode behavior and keeps catalogue flags before
resume arguments. Actual Codex 0.154.0 controls for gpt-5.4, gpt-6-astra and gpt-6-sol pass,
including the exact nested tools, audited MCP read and resumed turn. Catalogue-focused controls
also pass. Earlier fallback-model mutations do not establish new recognized-model/catalogue
coverage. Required/optional field semantics, malformed/output/time bounds, cancellation, resource
ownership, authentication/default preservation and recognized-model mutation checks remain
unfinished, as do current-tree lint/types/tests/schema/client/artifact/CI acceptance.

**Owner pause supersedes earlier release authorization:** checkpoint commit/push only. No merge,
tag or publication. 0.48.0 remains unreleased; latest published version is 0.47.3.

## Amendment — 2026-10-15: the reopened engine comparison is closed, and the decision above stands
The comparison reopened under Group 6 preferred a replacement interaction SDK for one reason: accessibility observations addressed by stable element handles, which the field has settled on because a handle to a named element survives a re-render where a coordinate does not. That reason does not hold. The owned engine at its pinned 1.63.0 already emits `[ref=eN]` handles from `aria_snapshot(mode="ai")`, offers bounding boxes and a depth bound alongside, and resolves a handle back to its element through the `aria-ref=` selector engine. Verified here rather than read from documentation: a snapshot reported `button "Submit" [ref=e2]`, the selector matched exactly one element, and clicking it ran the page's handler. `get_by_ref` is absent from this version's Python surface, so resolution goes through that selector and not that method.

The replacement was also never a replacement. Its engine class subclassed the owned one and still delegated tabs, console, requests and tab closure to it — its own note records that the SDK omits tab ids — along with the owned profile, CDP target identity, screenshot sizing and indexed locators. Adopting it meant carrying two engines, a pinned native binary and a lazy asset download instead of one engine. Against that, its three failing real controls are structural rather than defects: its documented surface carries no wait command or wait selector syntax at all, so a host must supply waiting itself, and its navigation raises a Chromium network error where the owned engine returns a response carrying an HTTP status, which is a boundary observation the origin controls assert on.

So the candidate is retired: its engine, native client, asset resolution and download step are removed, with the reference tests that only it could satisfy, and element handles are implemented on the owned engine instead. A handle belongs to the document that issued it, so handles are kept per tab, retired on leaving that document, and a handle nobody issued is refused by name rather than resolved — the engine would otherwise spend the caller's entire timeout failing, which two mutations measure. The spelling the caller reads in a snapshot is the spelling the `ref` argument takes. Nothing in the packaging changed, because the candidate was never a declared dependency.

Evidence: the whole browser directory at 49 passed, 3 failed, 2 skipped before retirement, with every failure on the candidate and none on the owned engine. This closes a comparison; it does not change the engine selected in the Decision above, and it adds no browser vocabulary to kernel or runtime.
