# Optional browser components

Install `shadow-hdk[browser]`. A base installation still exposes the pack's declarations;
invoking a browser without its extra returns an explicit failed observation.

```python
from shadow_hdk.adapters.browser import BrowserComponents, OriginPolicy, PlaywrightEngine

browser = BrowserComponents(
    engine=PlaywrightEngine(policy=OriginPolicy(origins=("https://example.org",)))
)
```

Supply `browser` among the host's ordinary component ports. Products choose whether to include
the pack, which actions to offer and how to judge their declared effects. `OriginPolicy` permits
HTTP(S) localhost and literal loopback addresses by default, plus the exact scheme, hostname and
effective port supplied by the host. Set `allow_localhost=False` for an exact allowlist alone.
An agent's action inputs cannot widen the policy.

Every action is an ordinary act with JSON inputs and the existing approval preview. Navigation,
clicking, typing, selecting, pressing keys, scrolling and opening/closing tabs declare writes;
reading accessibility snapshots, finding elements, waiting, inspecting tabs/console/requests and
taking screenshots declare reads. A read-only mode can inspect a browser already opened in its
scope; it cannot open one. `browser_type` uses a literal value, not a shell or JavaScript snippet.
Locators use either `selector` or `role`, with an optional exact accessible `name` for roles.
Ambiguous interactions require an explicit `nth` index. Unsupported arguments are refused.

The default engine is local, headless Playwright/Chromium. It creates a private profile and local
origin gateway per resource scope, without a person's cookies, credentials or browser profile.
Conversation/Thread own that scope across turns and approval pauses and release it on close.
A low-level run releases its resources when it ends, retaining them while parked. A host supplying
`RunOptions.resource_scope` owns its teardown. Browser processes do not survive host restart.

The first open operation reports preparation of an isolated mitmproxy SDK environment and, if
Chromium is missing, installation of its binary. Installation of HDK and catalogue construction
download no browser. Engine provisioning can download engine assets; page requests then pass
through the local gateway. `install_browser=False` lets a deployment provision binaries itself.
No cloud browser service or extra model loop is used.

The gateway checks redirects, HTTP(S) subresources, workers and WebSockets before contacting
their origins. Service workers are blocked. Chromium trusts only its disposable gateway CA's
public-key hash; no system CA is installed, and upstream TLS verification remains enabled.
`upstream_ca=Path(...)` allows a host's development CA explicitly. Chromium's non-proxied UDP
restriction prevents page WebRTC bypass. The acceptance controls run on Linux and macOS;
these mechanisms do not claim an OS-wide sandbox against a compromised browser engine.

`browser_open`, `browser_new_tab`, `browser_back` and `browser_forward` return HTTP status when
a response exists. `browser_console` and `browser_requests` return non-consuming bounded logs
(last 256 entries), optionally filtered by tab. Failed requests and HTTP error responses remain
visible. A blocked navigation may already have performed an allowed hop, so its observation is
failed rather than falsely claiming no action occurred.

Screenshots arrive in `Completed.images` and reach the model and MCP as image blocks, rather
than as base64 embedded in prose. The LangChain chat projection completes all text tool results
before adding their associated image carrier, as required by native chat message ordering.
Images are limited to 10 MB; full-page captures also have a 20-million-pixel limit. Snapshots
and element results name truncation. Arbitrary evaluation, uploads, downloads, remote browsers
and personal profiles are outside this pack's action vocabulary.

Playwright is Apache-2.0; mitmproxy is MIT; uv is MIT/Apache-2.0. Engines stay behind the
`BrowserEngine` protocol, so a host may supply another implementation meeting the same contract.

## Paused engine-selection candidate — 2026-10-13
The unreleased 0.48.0 checkpoint exports `AgentBrowserEngine` alongside the existing
`PlaywrightEngine`. `BrowserComponents` still defaults to Playwright. The agent-browser 0.39.0
candidate delegates interaction, accessibility observations and `@eN` element references to
its local native SDK; HDK retains declarations, preview/approval/audit, exact origin gateway and
owned private profile/process lifecycle. Target actions accept a `ref` in place of selector/role;
reference support is currently candidate-engine specific. No personal profiles or cloud session
are enabled. First use lazily fetches a pinned/integrity-checked native SDK and reports preparation.

The candidate is incomplete: combined real gate has 15 passed / 3 failed; HTTP-error navigation
and Playwright-specific wait selectors need compatibility work. Installer bounds/cancellation,
reference mutations and exact-current-tree gates remain pending. Original adapter stays available
until replacement acceptance. See ADR 0001 and Phase 67 tasks for comparison and limitations.
Owner has stopped implementation/release work; this documents WIP, not released support.
