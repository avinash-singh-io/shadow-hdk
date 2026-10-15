# History

## 2026-10-13
- [DECISION] Owner approved all four corrections and proper release, following the recommendation as 0.48.0. This is advance authorization for staging → main, tag, GitHub release and PyPI publication.
- [DISCOVERY] Runtime proof: SocketOffer is not Narrowing, its holder is. Existing tests exercise Routing/RecordingServer and miss the production wrapper.
- [DECISION] Preserve tracked files under Git ignore semantics; use exact ownership for custom branches. Existing environment mechanisms remain maintenance-only under D190.
- [START] Group 0 complete. Phase 67 and v0.48.0 claimed. Starting N-W0 red proof.

- [VERIFY] Group 1: production socket/relay mode-switch regression plus existing controls, 10 passed. Removing forwarding kills both catalogue/call and execution assertions; source restored byte-for-byte, 2 restored controls pass.
- [DISCOVERY] okf index regeneration removed curated decision records; restored the prior curated indexes rather than accepting that unrelated deletion.

### [SCOPE_CHANGE] 2026-10-13 — Owner expands the next release to optional primitives
Topics: browser, background-jobs, host-access, test-results, codex, component-packs
Affects-phases: phase-67-workbench-corrections
Affects-specs: specs/project-rules.md#D190
Detail: The owner explicitly authorizes adding a browser, N-W1/N-W5/N-W6 and Codex audited reads to the next release, using validated open-source engines under optional ports. This supersedes the original maintenance-only exclusion; interactive PTY and product changes remain out. The active goal continues until this expanded acceptance and publication are verified.

---

### [DISCOVERY] 2026-10-13 — A routing allowlist leaks through a second redirect
Topics: browser, origin-policy
Affects-phases: phase-67-workbench-corrections
Affects-specs: specs/decisions/0001-optional-workbench-packs.md
Detail: A real isolated Chromium 1.63.0 probe observed a blocked server receive a request through an allowed-to-allowed-to-denied redirect chain. Context routing with fetch(max_redirects=0) plus checking each visible Location is insufficient because the browser's subsequent redirect bypasses that handler. The candidate is rejected; origin enforcement needs an independent interception/proxy boundary and the same counterexample must pass before the browser ships.

---

### [FEATURE] 2026-10-13 — Corrections and initial image contracts verified
Topics: worktrees, search, snapshots, images, resources
Affects-phases: phase-67-workbench-corrections
Affects-specs: docs/developer-guide.md, specs/architecture/overview.md
Detail: Host-named branch controls and seven ownership mutations pass; a recreated checkout with the same path/branch is distinguished by a private Git-administration birth marker, including the default-prefix path. Ignore-aware search and history mutations pass, with a 100k tracked + 100k ignored CI benchmark control below all budgets. The current generic image/wire/resource candidate passed a full suite of 2,293 tests (29 skipped, 25 deselected), with fresh lint/format/types; after the birth-marker correction, 24 worktree controls pass. Group 5 remains in progress: resource lifetime through parked approvals and multi-turn sessions still requires acceptance before the browser ships.

---

### [FIX] 2026-10-13 — Resource lifetime follows a conversation across turns and approvals
Topics: resources, approvals, conversation, wire, BUG-241
Affects-phases: phase-67-workbench-corrections
Affects-specs: specs/decisions/0001-optional-workbench-packs.md
Detail: Two new controls failed because cleanup ran at park and at each turn. RunOptions now accepts a host-owned opaque scope; root defaults retain resources during a park, while Conversation/Thread hold their scope across turns and settlement. Scope crosses run and resume callbacks. Resource aliases release once, every port is attempted after an error, and close settles before delivering cancellation. Additional failing controls reproduced leaked Thread store holds after cancellation/failure and repeated cancellation (BUG-241); the complete close now settles resource and store teardown together. Fourteen focused lifecycle/wire controls pass, with broader conversation/park/restart controls passing; mutation verification is in progress. Browser, workbench packs, Codex read correction and publication remain pending.

---

### [FEATURE] 2026-10-13 — Optional browser candidate verified
Topics: browser, images, origins, installation, optional-packs
Affects-phases: phase-67-workbench-corrections
Affects-specs: docs/browser.md, specs/decisions/0001-optional-workbench-packs.md
Detail: The direct Playwright engine uses an isolated pinned mitmproxy SDK process with per-profile TLS interception before upstream connection, retaining upstream certificate verification. Restored controls pass 41 tests including first-use binary installation, real multi-turn images, allowed TLS/sockets, denied HTTP/TLS zero connections and a positive/negative UDP probe. All 32 browser mutants and the rechecked 14 generic image/wire mutants are detected. The installed base wheel exposes 17 declarations without SDK imports and includes its gateway resource. Two independent CI browser legs are added. Group 7 has initial host/job/report controls and new red proofs for split UTF-8 and descendants of exited leaders; its implementation is still in progress. Codex correction and final release acceptance remain pending; 0.47.3 is latest published.

---

### [FEATURE] 2026-10-13 — Workbench and governed Codex controls pass
Topics: background-jobs, host-access, test-results, codex, resources, wire
Affects-phases: phase-67-workbench-corrections
Affects-specs: docs/workbench.md, docs/for-a-product.md, specs/architecture/adapters.md, specs/architecture/runtime.md, specs/architecture/wire.md
Detail: Twenty-six workbench mutations detect independent-cursor, metadata, listener, file-door and report regressions. BUG-242/243 fix split UTF-8 and owned children surviving exited leaders. Eight Codex mutants detect private bootstrap, uninjected defaults, cleanup, native shell/image exposure and capability drift. A real Codex 0.154.0 SDK uses a local deterministic Responses model, crosses the real MCP socket and records the file read, then resumes with the same governed catalogue. MCP resource discovery remains; the kit relay exposes no filesystem resources. Teardown is explicitly negotiated so older TypeScript clients retain the no-resource default; five built-client mutations detect scope loss, duplicate owners, hidden failure, missing raw owner and missing negotiation. Restored combined controls pass 23 cases; full release acceptance remains Group 9.

### [ARCH_CHANGE] 2026-10-13 — Synchronize accepted additive contracts at release preparation
Topics: resources, images, codex, browser, workbench, spec-drift
Affects-phases: phase-67-workbench-corrections
Affects-specs: specs/architecture/file-structure.md, specs/architecture/runtime.md, specs/architecture/adapters.md, specs/architecture/wire.md
Detail: Record the accepted ADR's optional image observations, resource scope/cleanup negotiation, private CLI bootstrap directory and optional browser/workbench adapter map. No product or native successor specification is edited. All implementation groups have candidate evidence; release preparation now performs the documentation sync and final gate.

### [VERIFY] 2026-10-13 — Local release acceptance passes
Topics: acceptance, packaging, benchmark, landing
Affects-specs: specs/status.md
Detail: Full expanded local suite: 2,357 passed, 29 skipped, 25 deselected; lint/format/strict types pass over 552 files. All five benchmark cases pass. Installed 0.48.0 wheel controls outside source on Python 3.12: 69 passed, one first-use control skipped (that control passes in the full source gate). Base-wheel no-engine/no-browser catalogue and explicit missing-extra behavior pass. Pinned CPython smoke passes. Exact-head CI, landing and publication remain pending.


### [PAUSE] 2026-10-13 — Owner stops implementation and release
Topics: pause, browser-selection, codex, checkpoint, release-gates
Affects-specs: specs/status.md, specs/decisions/0001-optional-workbench-packs.md
Detail: Owner requests all Phase 67 work committed and pushed, then goal paused; explicitly forbids merge, tag and publication. Preserve comparison and unfinished Codex verification, with inline handoff only. Pinned local comparison favors agent-browser 0.39.0 for references/observations and small daemon footprint, but it is not accepted: combined real browser gate completes 15 passed / 3 failed, all candidate failures (HTTP error navigation and two Playwright-specific wait-selector cases). Original Playwright remains default. Three recognized-model actual Codex 0.154.0 controls pass (gpt-5.4, gpt-6-astra, gpt-6-sol, including resume); new catalogue mutations/edge controls remain pending. Earlier 2,357-pass suite, types and installed-wheel controls predate these changes. No active mutation runner or owned browser/test process remains; earlier exact restoration and restored controls are preserved. No new mutation or acceptance run is started after stop. Checkpoint is not release acceptance.

### [DISCOVERY] 2026-10-15 — Playwright carries the reference pattern the candidate was chosen for
Topics: browser-engine, element-references, group-6
Affects-phases: phase-67-workbench-corrections
Affects-specs: specs/decisions/0001-optional-workbench-packs.md#options-considered
Detail: The installed Playwright 1.63.0 already emits `[ref=eN]` element references from
`aria_snapshot(mode="ai")`, and also offers `boxes` for bounding boxes and `depth` for size
control. Accessibility observations with stable references were the capability the replacement
candidate was preferred for, so the comparison's premise no longer holds. `Page.get_by_ref` is
absent from the Python API at this version; resolution goes through the `aria-ref=` selector
engine, which is verified here: a snapshot of a small page reported `button "Submit" [ref=e2]`,
`locator("aria-ref=e2")` matched exactly one element, and clicking it ran the page's handler.

---

### [ARCH_CHANGE] 2026-10-15 — Group 6 becomes references on the owned engine, not an engine swap
Topics: browser-engine, group-6, dependencies
Affects-phases: phase-67-workbench-corrections
Affects-specs: specs/decisions/0001-optional-workbench-packs.md#decision
Detail: `AgentBrowserEngine` subclasses `PlaywrightEngine` and still delegates tabs, console,
requests and tab closure to it, along with the owned profile, CDP target identity, screenshot
sizing and indexed locators, so the candidate was additive rather than a replacement: two engines,
a pinned native binary and an asset installer in place of one. Its documented surface carries no
wait command or wait selector syntax, which is both selector failures, and its navigation raises a
Chromium network error where the owned engine returns a response carrying an HTTP status, which is
the third. Recommendation recorded for owner confirmation: keep the owned engine, take the
reference pattern onto it, and retire the replacement candidate rather than finish accepting it.

---

### [DISCOVERY] 2026-10-15 — What the field settled on, and where this pack sits against it
Topics: browser-engine, element-references, live-view, phase-68
Affects-phases: phase-67-workbench-corrections, phase-68
Affects-specs: none
Detail: Surveyed how current agent systems drive browsers, at the owner's request, before deciding
the engine. The settled pattern is an accessibility tree read first and addressed by numbered
handles, with screenshots on demand rather than as the primary observation, because a handle to a
named element survives a re-render that a coordinate does not, and because a tree costs a fraction
of a screenshot's tokens. One tool pairs them by labelling an annotated screenshot with the same
handles. Systems that let a person watch split between a CDP screencast of the owned page and a
VNC view of a whole virtual desktop, and the ones that also let a person take over forward input
events back over the same channel. This pack is already on the settled pattern and its origin
boundary is ahead of it — a widely used server's own documentation warns that its allowed-origins
option is not a security boundary, where this one was proven against redirects, subresources and
WebSocket CONNECT. What the pack lacks is the watching half, filed as ENH-053 with the transport
decided and the reasons recorded, so phase 68 starts from the decision rather than the survey.

---

### [DISCOVERY] 2026-10-15 — A governance control's result depends on where it is run from
Topics: codex, governed-launch, test-hermeticity, installed-controls
Affects-phases: phase-67-workbench-corrections
Affects-specs: none
Detail: Building installed-wheel controls for 0.48.0 surfaced TD-023. The real-Codex governance
control passes from the checkout and fails from a copied test tree, where the governed launch
carries flat function tools — including three that belong to a product and appear in this
machine's own SDK session rollouts — instead of the single nested namespace tool expected. The
control sets an isolated home and a temporary workspace, so the route by which those tools
arrived is unexplained; the repository root does carry a `.codex/` directory the copied tree
lacks, which is the likeliest cause but is not established. Recorded as unexplained rather than
benign, because the pack claims a private bootstrap and an isolation gap there would be
security-relevant. Excluded from the ad-hoc installed selection with the exclusion stated; it is
unaffected for the release, since CI runs it from a checkout where it passes.

---
