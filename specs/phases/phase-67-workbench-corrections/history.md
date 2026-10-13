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
