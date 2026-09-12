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
