# Workbench primitives — reply to Intent Studio lane P

**0.48.0 candidate; paused by owner, not released.** The owner authorized these optional harness
components on 2026-10-13. Latest published release remains 0.47.3. Current authorization is checkpoint commit/push only; no merge, tag or publication.

| Need | Candidate behavior | Integration |
|---|---|---|
| Browser | Local headless Playwright, isolated profiles, exact host origins, governed action previews, accessibility/interaction/tabs, native screenshots, console and request diagnostics, lazy installation and owner cleanup | Register `BrowserComponents` with a host-supplied `PlaywrightEngine`/`OriginPolicy`; install `[browser]`. See `docs/browser.md`. |
| N-W0 | Socket offer forwards mode narrowing at open and mode switch, for listings and calls | Existing host paths gain the correction; the product may validate and retire `_NarrowingSocketOffer`. |
| N-W2 | Optional host-named branch; exact creation identity controls cleanup | Supply the branch on worktree creation. Existing defaults are retained. |
| N-W3 | Git ignore semantics, nested portable ignores, no traversal file ceiling | Existing glob/grep paths gain the correction; tracked ignored files remain visible. |
| N-W4 | Reused private index and targeted restore | Existing checkpoints gain the correction; ignored data and the user's HEAD/index/stash are preserved. |
| Codex reads | Native world tools disabled; private SDK startup prevents repository discovery reads; MCP file reads are ordinary kit acts | Three recognized-model controls pass on CLI 0.154.0 including resume. New catalogue mutation/edge controls and final acceptance unfinished. See migration notes. |
| N-W1 | Owned background jobs, non-consuming output cursors, metadata, output URL hints and optional verified TCP listeners, stop including descendants | `HostDoor`, `WorkbenchComponents`, existing background command tools; install `[workbench]` for local listener inspection. |
| N-W6 | Direct command/file access in the same host environment, with no agent | `HostDoor`, under the person's own host authentication/environment policy. PTY is later. |
| N-W5 | JUnit counts, failing names, failure/error/skip details, case/suite output; malformed/incomplete/entity reports refused | `HostDoor.results` or governed `test_results`; install `[workbench]`. |

Products decide which packs to register and offer, modes, origins, authentication, UI and pins.
No product code or bridge is changed here. Browser state survives turns and approvals within its
owner's live process, and closes with that owner; it does not survive host restart. New wire
resource ownership needs the updated runtime/client together.

Evidence is under `specs/phases/phase-67-workbench-corrections/evidence/`. The fixed 100k tracked
+ 100k ignored fixture reports search/checkpoint/restore budgets independently in CI. A separate
upstream CPython v3.14.0 smoke at `ebf955df7a89ed0c7968f79faec1de49f61ed7cb` exercises 5,220
tracked files and restores a real external edit without changing HEAD or the person's index.
These are measured fixtures, not a guarantee of constant-time checkpoints on every repository.

Release acceptance still requires full local/CI gates, seven published artifacts and fresh
index installs. This record will be updated when publication is verified.

Browser selection is reopened: agent-browser 0.39.0 is the preferred local candidate, with
public `ref` arguments, but its combined real gate has three failures (15 pass). Playwright
remains default. Comparative evidence and pending replacement gates are in ADR 0001 and Phase
67 tasks. No product bridge retirement or new released capability is implied by this checkpoint.
