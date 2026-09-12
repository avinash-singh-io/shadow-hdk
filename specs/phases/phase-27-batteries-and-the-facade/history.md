---
type: History
phase: 27
---

# History — Phase 27

Append-only. Decisions as `### [DECISION] date — D<n>: title`; the index in
`specs/decisions/index.md` is regenerated from them.

### [NOTE] 2026-09-12 — Opened

Topics: batteries, facade
Affects-phases: phase-27-batteries-and-the-facade
Affects-specs: planning/the-substrate.md#3.6, planning/the-substrate.md#3.7
Detail: Cut from `main` after Phase 26 landed (v0.23.0). The plan is `planning/the-substrate.md`
§3.6 (built-in tools, consumed) and §3.7 (the facade); the owner's word for the lease in the file
and the facade is `budget`.

---

### [DECISION] 2026-09-12 — D70: a battery is a file — an MCP server or a callable consumed behind the component port, its effects vouched for, judged by the modes as they are

Topics: batteries, mcp, web-search, effects, registry, licence
Affects-phases: phase-27-batteries-and-the-facade
Affects-specs: planning/the-substrate.md#3.6, architecture/overview.md

**The survey, run here.** wigolo 0.2.1 (`npm view`: AGPL-3.0-only, Node ≥ 20, 6.4 MB unpacked,
796 MB of dependencies installed into the scratchpad, never globally; its models download on
first use) starts as a stdio MCP server in ~1.5 s and lists ten tools — `search`, `fetch`,
`crawl`, `cache`, `extract`, `find_similar`, `research`, `agent`, `diff`, `watch` — **none with
MCP annotations**, so the adapter's rule (derived, not trusted) would register every one as the
worst case and no mode would offer it. `ddgs` (PyPI, MIT, DuckDuckGo, no models) is the light
alternative, a callable rather than a server.

**A battery is a file.** `[battery]` names the server — `kind = "mcp"` with a `command` resolved
on PATH or through `bin_env` (the providers' convention: `WIGOLO_BIN`), or `kind = "python"` with a
`callable` and what it `requires` — its `licence`, and what would `install` it; `[tools.<name>]`
names the server's tool to expose under the harness's name (`web_search`, `web_fetch`) and the
**effects a deployment vouches for**. The vouching is the point, and it is the *"until a
deployment says otherwise"* the MCP adapter's docstring always allowed for: `McpComponents`
grew `only=`, `aliases=`, `effects=` — the rest of a server's tools are not registered at all.
`BatteryRegistry` reads sources — the shipped files, a directory, a store (`store_batteries`,
D66) — later shadowing earlier; a document that will not load is a reported problem; a battery
whose command or package is absent is a problem naming what would install it, never a silent
absence.

**Honest effects, no new rule.** A battery is its own process, outside the environment's
sandbox, and it reaches the web: `reaches = true, contained = false`, writes nothing of ours.
The shipped modes judge that as they judge anything — `workspace-write` requires containment and
refuses it by its ceiling; `read-only` reads the web as it reads anything; `full` allows. A
product that wants the web inside a confined mode makes a mode (data, D64) whose ceiling says
so. No rule was added for batteries.

**The licence at arm's length.** wigolo runs as its own process over stdio and is never
imported or linked; the battery file says so where it is read. Whether that is enough for a
product is the lawyer's read on the owner's row, not the harness's claim.

*Why:* principle 5 — build the loop, consume the rest: the two tools every agent product asks
for first arrive as data over a port that already existed, with zero adapter code for wigolo
and twenty lines for ddgs; and principle 10 — a battery written now is a battery at the next
read.

---

### [NOTE] 2026-09-12 — Group 2 measured: wigolo live through the studio; serve outlived its SIGTERM

Topics: batteries, wigolo, serve, shutdown
Affects-phases: phase-27-batteries-and-the-facade
Affects-specs: none
Detail: `[tools] batteries = ["wigolo"]`, `WIGOLO_BIN` naming the scratchpad install, the thread in
`read-only` (the mode whose ceiling offers a battery — `workspace-write` hides it by its own
profile, measured in a test with the sandbox). One turn on Claude Code through the page over the
wire: `web_search` (wigolo, ~1.5 s to warm) returned the npm page with the version in its snippet;
`web_fetch` of npmjs.com came back `blocked_by_challenge` — the battery's honest failure, shown
as a failed item; `web_fetch` of `registry.npmjs.org/wigolo/latest` succeeded; the agent answered
0.2.1 / AGPL-3.0-only with both sources and wrote nothing. 3 tool calls · 27¢. `batteries/list`
said `wigolo:on`, `ddgs:off`. Stopping the preview found `serve --http` alive minutes later with
its provider and wigolo: uvicorn's graceful shutdown waits for the page's open SSE stream — the
lesson the studio's own server had learned (`timeout_graceful_shutdown=2`) and the move to
`serve` had lost. Fixed where `serve` builds its server; a test sends SIGTERM with a stream held
open and requires the process gone within eight seconds (RED: outlived it).

---

### [DECISION] 2026-09-12 — D71: one package is the host's front door — `Harness` in `shadow-hdk-serve`, three lines by default, one step deeper without leaving it

Topics: facade, harness-toml, budget, serve, invariants, examples
Affects-phases: phase-27-batteries-and-the-facade
Affects-specs: planning/the-substrate.md#3.7, architecture/overview.md

**Where the facade lives.** `shadow-hdk-serve` already held the shipped composition
(`ServeHost`, `a_thread`) and the console script; the facade is the same composition with a
product's front door on it, in-process — so it lives there too, and one package is the door
whichever way a product comes in: `Harness.load("harness.toml")` in Python, `shadow-hdk serve
harness.toml` from anywhere else, the same file in both hands. A separate `shadow-hdk`
umbrella package was considered and refused: the kernel/runtime/adapters split is what keeps the
stands-alone rule checkable, and a package that only re-exports is one more thing to version.

**Three lines.** `async with Harness.load(path) as h:` opens a thread on the provider signed in
here inside the workshop; `async for part in h.turn(text):` yields every part of what happens,
in order — the record's events by their own kind, `activity` beside them (D63), `item` as each
step folds closed (D46, one fold, the runtime's), and `turn` last with the record. `Harness(root,
mode=…, batteries=…, budget=…)` is the file without the file. The thread's record stays readable
after close.

**One step deeper, without leaving.** `governance=`, `sink=`, `observer=` and `agent=` hand a
product's own port in for the shipped one and keep the rest; `.thread`, `.host`, `.approvals`,
`.modes`, `.rules`, `.store` are the objects underneath, for everything else. Two invariants hold
the promise that nothing done through the facade is closed to a product that goes deeper: the
facade imports only names in the `__all__` of the packages it composes and touches nothing spelled
private (an AST walk; a private import and a private attribute both measured to fail it), and
every `harness.toml` key maps to a port, a port's argument or a kernel profile (a table walked
against the loader's `KNOWN` and the tree; a key with no meaning measured to fail it).

**`budget`.** The file and the facade say `[budget] steps · seconds · cents` — the owner's word —
and the kernel says `Lease(Ceiling, Floor)` underneath; `Budget.lease()` is the whole translation.

**The examples.** The coder is the facade now — its REPL over `Harness`. The host example
stays what it is: the demonstration of composing the ports yourself (its own policy, ledger,
checkpointer, a brief parked and resumed from the next process) — the level the facade's
invariants promise stays open. Reducing it to the facade would have removed the thing it shows.

*Why:* principle 9 — simple by default, deep by choice — is only true if the simple path is a
few lines *and* the deep path is the same objects; the invariants are what keep the second half
from drifting.

---

### [DECISION] 2026-09-12 — D72: the optimiser is a port over documents with slots, gated by the sink, and its evaluator is locked before any loop

Topics: optimiser, dspy, evaluator, rule-11, proposals
Affects-phases: phase-27-batteries-and-the-facade, phase-28-context-engineering
Affects-specs: architecture/optimiser.md

Specified in `architecture/optimiser.md`, not built. What an optimiser may change is already data
— a mode's behaviour, a skill's text, a pattern's prompts, a battery's descriptions — so a
*program* is a document with the slots it may rewrite, and fields governance reads (a mode's
policy, a battery's effects) are never slots. `OptimiserPort.improve(program, evaluator, budget)
→ Improved` carries before/after scores and the evaluator's version; the result is a
`Proposal(kind="optimisation")` through the sink, kept by the host like a minted skill (D56) —
never an edit to a running registry. The evaluator is `(version, corpus, score)`, locked before
the first loop (Rule 11), affordable through the recorded model port (Phase 8) and the scripted
doubles; `v1` is a commit that precedes any implementation. DSPy is the reference behind it —
instruction ↔ the `system` slot, trainset ↔ corpus, metric ↔ score — consumed as one adapter that
imports nothing of ours but the kernel and the runtime; a `HillClimb` in `basic` is what makes the
port's contract suite run without it.

*Why:* an optimisation loop with a mutable evaluator measures motion, not progress (Rule 11);
settling the port's shapes first means the loop, when it is built, is measured against something
not written to flatter it.

---

## Verification Evidence

Captured fresh 2026-09-12 on the phase branch at close, before landing:

- `uv run ruff check -q` → exit 0
- `uv run ruff format --check -q` → exit 0
- `uv run mypy` → exit 0 (`Success: no issues found in 237 source files`)
- `uv run pytest -q -p no:cacheprovider -m 'not live'` → `1364 passed, 2 skipped, 12 deselected, 85 warnings in 146.90s (0:02:26)`
- `tests/test_versions.py` → EXPECTED `0.24.0`, eighteen packages moved together (D9); `uv sync --all-packages` clean
- RED first, every group: group 1 `ModuleNotFoundError: shadow_hdk.serve.batteries`; group 2 `unknown table [tools]`, `Settings() got an unexpected keyword 'batteries'`, `a_thread() got an unexpected keyword 'agent'`; the SIGTERM test *outlived SIGTERM while a page held the stream*; group 3 `cannot import name 'Harness'`; the two invariants proven to bite by mutation (a private import, a private attribute, a name not in `__all__`, a key with no meaning — each failed the build)
- Mutation passes: group 1 seven killed (only/aliases/effects ignored; absent command unreported; store not shadowing; `requires` unchecked; effects optional); group 2 five killed (unknown id unreported; batteries not offered; `aclose` forgetting without closing; listing says on for all; `a_thread` ignoring batteries); README's Python snippet and TypeScript snippet each fail on a wrong line
- Live, on the owner's subscription (Claude Code 2.1.235), through the studio served by `shadow-hdk serve --http --page … $SC/harness.toml` with `[tools] batteries = ["wigolo"]`, `WIGOLO_BIN` naming the scratchpad install, the thread in `read-only`: `batteries/list` → `wigolo:on`, `ddgs:off`; one turn — `web_search` (wigolo) returned the npm page with the version in its snippet; `web_fetch` of npmjs.com came back `blocked_by_challenge` and was shown as the failed item it is; `web_fetch` of `registry.npmjs.org/wigolo/latest` succeeded; the answer named 0.2.1 / AGPL-3.0-only with both sources and wrote nothing — 3 tool calls · 27¢; wigolo ended with serve
- wigolo itself: `npm i wigolo@0.2.1` into the scratchpad only (796 MB of dependencies), started as a stdio MCP server in ~1.5 s, ten tools listed, none annotated — the survey behind D70

---
