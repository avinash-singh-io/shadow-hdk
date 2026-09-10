---
type: History
phase: 20
---

# History — Phase 20, Providers

### [DECISION] 2026-09-11 — D39: inference and agency are two seams, not one interface

Topics: providers, model-port, agent-port, subscription
Affects-phases: phase-20-providers
Affects-specs: architecture/overview.md

An API key sells **inference**: messages and tool schemas in, text and tool calls out, the caller
owning the loop. A subscription sells **an agent**: a prompt in, work done, a stream out, and it
owns its own loop, its own conversation and its own choice of tool. `ModelPort` is the first;
`AgentPort` is the second, under D22's open port set.

The tempting alternative was one interface with a CLI-backed `ModelPort` behind it. It cannot be
built honestly: extracting a single tool call from a coding CLI means defeating its own loop, and
none of them supports that. The reference implementation carries twenty-eight provider definitions
and no `complete(messages, tools) -> tool_calls` seam anywhere — not an oversight, a finding.

*Why:* one interface over two products would have to lie about one of them. *Overturned by:* a CLI
that grows a real single-step completion mode, which would make it an inference provider and it
would arrive at the first seam.

---

### [DECISION] 2026-09-11 — D40: a provider is data, like a pattern

Topics: providers, toml, d17
Affects-phases: phase-20-providers
Affects-specs: architecture/file-structure.md

D17 made agent architectures TOML a team writes without touching Python. A provider is the same kind
of fact — a binary, some probes, some environment rules, a transport — and is stored the same way.
Adding a CLI is adding a file; only a genuinely new transport costs an adapter.

This is taken from the reference **and corrected where it decayed**. Its provider record is data,
but two things leaked back into per-provider code: the spawn environment is a hand-written branch
per agent, and authentication failure is classified by a per-agent function matching English error
text. Both are fields on the record here. Every time provider knowledge leaks into a code path,
adding the next provider costs a phase again.

*Why:* the second provider must cost a file. *Overturned by:* a provider whose quirks genuinely
cannot be expressed as data — which would be evidence the record is missing a field, not that the
rule is wrong.

---

### [DECISION] 2026-09-11 — D41: the harness asks; it never reads a credential and never installs

Topics: providers, auth, subscription
Affects-phases: phase-20-providers

Authentication belongs to the CLI that already has it. This runtime asks a provider its own status
question and reads the answer. **No credential is opened, stored, forwarded or logged** — there is
nothing to leak because nothing is held.

The answer has five shapes and none is a guess: `ready · absent · not-signed-in · too-old ·
unknown`. *Unknown* is honesty, not failure — some CLIs cannot be asked, and a runtime that reported
*not signed in* because it could not tell would send people to fix what is not broken.

A provider that is absent is reported with the command that would fix it. Installing it is not this
library's business, on this machine or anyone's.

*Why:* the smallest credential surface is none. *Overturned by:* nothing foreseeable; a provider
needing us to hold a secret is a provider for the first seam, where the host holds it.

---

### [DECISION] 2026-09-11 — D42: the socket — every effect routes through the run's registry

Topics: providers, governance, injection, effects
Affects-phases: phase-20-providers
Affects-specs: architecture/overview.md

If a subscription-backed agent runs its own loop, what is left of governance? Everything that
matters, provided one invariant holds: **every effect routes through the run's component registry,
whoever decided to call it.**

For a model provider this is already true. For an agent provider it is made true by injection: the
provider is launched with the run's own registry as its tool source and its native tools refused, so
a file it writes, a command it runs and a claim it proposes all arrive as `Invoke` on our graph —
judged on effects rather than names, charged to the parent's lease, stamped with a posture, on the
event stream, and with the sink still deciding what is kept.

This is *govern effects, not names* raised one level: the harness does not govern a provider, it
governs the effects. It is also the difference between this and the reference, which injects tools
where this injects **governed** tools.

*Why:* it is the only claim that makes the two seams equally safe. *Overturned by:* a provider that
cannot be made to take injected tools, which cannot be governed here and must be refused rather
than admitted ungoverned.

---

### [DECISION] 2026-09-11 — D43: the loop stays theirs, and that is the price on the label

Topics: providers, patterns, subscription
Affects-phases: phase-20-providers

When a subscription drives, this runtime's patterns and compositions do not run. We own the tools,
the judgement, the lease and the record; the provider owns the reasoning.

Recorded as a decision rather than left as a gap, because it will be read as one. It is inherent:
you cannot buy an agent and also own its loop. A host that needs this runtime's loop uses
`ModelPort`, which is what it is for, and the choice between them is a real choice a host makes
rather than a limitation to be engineered away.

*Why:* naming the trade is what stops somebody spending a phase trying to have both. *Overturned
by:* nothing — this is a property of what a subscription sells.

---

### [NOTE] 2026-09-11 — what was measured, and what each measurement cost to find

Topics: providers, claude-code, opencode, measurement
Affects-phases: phase-20-providers

Four facts that no amount of reading the help text would have produced, each now a field:

**`CLAUDECODE` must be stripped.** Claude Code refuses to start inside another Claude Code session
and names the variable to clear. Inherited, the child dies before the handshake and the failure
arrives as a JSON-RPC *internal error* with the real cause on a stderr nobody was reading.

**`claude auth status` is the probe, not `claude auth`.** The latter is the command *group*: it
prints usage and exits 1. The first draft of the provider file said `["auth"]` and every install
came back `unknown`. Found by running the README's own snippet rather than by reading it.

**`USER` is load-bearing.** With `HOME`, `PATH` and `SHELL` alone, `claude auth status` answers
`"loggedIn": false` on a machine that is signed in — it resolves the credential by user. Bisected
against claude 2.1.235: of `USER`, `LOGNAME`, `TMPDIR`, `XPC_SERVICE_NAME` and `SSH_AUTH_SOCK`,
only `USER` flips it. Left out, this library reports a working subscription as unusable and sends
somebody to log in again — the exact failure the fifth status exists to prevent, arriving through
the back door of a too-thin environment.

**A TOML literal string needs no escaping.** The signed-out pattern was written with doubled
backslashes, so `"loggedIn": false` matched nothing: a pattern that is present, plausible and
inert, turning a signed-out install into `unknown` rather than `not-signed-in`. It has a test now
that runs the regex against a real answer.

Three of the four are *wrong answers* rather than errors, which is why each has a regression test
of its own — nothing else in the suite would have noticed.

The point of recording them together: **every one was fixed by editing a file.** That is D40's
claim, and this is the evidence for it.

---

### [NOTE] 2026-09-11 — the second provider cost a file

Topics: providers, opencode, d40
Affects-phases: phase-20-providers

`opencode` 1.18.21 was already on this machine, and `opencode acp` is a documented subcommand — it
speaks the transport Claude Code needed an npm bridge for. Adding it changed **no Python**: no
adapter, no branch, no code path that names it. One TOML file.

Measured: `--version` prints `1.18.21`; `auth list` exits 0 and prints the credential *names* it
holds, never the values, ending in a count. Not measured, and marked so in the file: the signed-out
wording, because observing it would mean signing somebody out. Until then an unmatched answer is
`unknown`, which is what the fifth status is for.

Detection, end to end, on this machine:

```
Claude Code  ready  2.1.235
OpenCode     ready  1.18.21
```

---

### [DECISION] 2026-09-11 — D44: the registry is connected to, never launched

Topics: providers, recording, injection, mcp
Affects-phases: phase-20-providers
Affects-specs: architecture/adapters.md

`RecordingServer` holds a live `RunContext` — the parent's lease, the parent's event stream — so it
is not a program that can be started; it can only be connected to. Phase 5 said exactly this in
`pipes.py` and named streamable HTTP as the answer for a child we do not spawn.

A coding CLI is that child. It launches its own MCP servers from a configuration it is handed and
will start whatever program that configuration names, and the program it starts cannot be our
server. So the program it starts is a **relay**: it connects to a loopback port we are already
listening on and copies bytes both ways. The child believes it started an MCP server; the server it
reached is the run's own registry, in this process, with the lease and the record intact.

Recorded as a decision rather than left as plumbing because it introduces a **console script that
ships inside an adapter**, which is a new kind of thing here, and because it puts the run's registry
on a socket. The port is loopback and ephemeral and the address is the caller's to keep: any process
on this machine that guesses it reaches the registry. That is the trust boundary `served_over_http`
already argues about, and it takes the same answer — a session-scoped token, when `wire.md`'s run
token is built.

*Why:* it is the only shape that works for a child we do not spawn. *Overturned by:* a CLI that will
accept an already-listening MCP endpoint directly, which would make the relay unnecessary for that
one and leave it needed for the rest.

---

### [SCOPE_CHANGE] 2026-09-11 — a second transport, and why the plan grew one

Topics: providers, transports, jsonl, codex
Affects-phases: phase-20-providers

The plan had one transport, `acp`, and a provider record for Claude Code naming it. That record was
a promise the file could not keep: Claude Code does not speak ACP natively — it speaks it only
through an npm bridge nobody should have to install.

The reference implementation does not use that bridge either. It drives Claude Code through the
CLI's own `-p --output-format stream-json` mode, and reading its provider definitions showed why the
shape generalises: **the unit of extension is the transport, not the agent.** Four or five stream
formats carry twenty-eight CLIs there; the marginal agent is free because the format was already
paid for.

So the plan grew `jsonl`, and with it `Dialect` — the names one CLI uses, as data. Three providers
now ship across two transports, and `codex` cost a file because the transport written for Claude
Code already existed.

Said as a scope change rather than slipped in as implementation: it is a second adapter and a new
kernel record, which is a plan amendment by any reading of Rule 10.

---

### [NOTE] 2026-09-11 — the live proof, and the four things it took to get there

Topics: providers, claude-code, injection, measurement
Affects-phases: phase-20-providers

The example runs. Claude Code reasons on the subscription; **our** components act:

```
  · write_file
    → Completed(output={'path': 'primes.py', 'bytes': 416})
  · run_shell
    → Completed(output={'exit_code': 0, 'stdout': '2 3 5 7 11 13 17 19 23 29 31 37\n'})
```

Each of those is a child run on the parent's graph, judged before it happened and charged to the
lease. The file is on disk and the agent never touched it.

Four things stood in the way, and every one is now a **field** rather than a code path:

**Its own permission layer.** The child answered *"Claude requested permissions to use
mcp__shadow-hdk__write_file, but you haven't granted it yet"* and stopped — its own prompt, in a
run where nobody can answer. Naming our server to `--allowedTools` removes *its* gate so the run's
governance is the only one left, which is the arrangement D42 wants: one authority, and it is ours.

**The prefix.** It lists injected tools as `mcp__<server>__<tool>` and accepts `mcp__<server>` for
all of them. That convention is the CLI's, so it is on the record.

**The driver was on offer.** The step that holds the conversation open lives in the registry, so the
child was offered a `converse` tool that re-enters the conversation it is already inside.
`RecordingServer` takes `withhold` now: what a parent offers a child is the parent's choice, and
`visible()` answers *what may this run do*, which is a different question.

**An `EffectProfile` of booleans.** `reads` and `writes` take a `ScopeSet`; passing `True` ended the
run with a `TypeError` out of the governance port — correct behaviour (D7), from a mistake that
should never have reached a run. `examples/` was outside `mypy`, and is not any more; that caught it
in a second and closed **ENH-004** on the way, since the example made `Ports.model` being required
into a real obstacle rather than a documented wart.

---

