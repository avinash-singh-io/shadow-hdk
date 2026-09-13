---
type: History
phase: 2-the-spike
---

# Phase 2 — history

Append-only. Newest at the bottom.

| Entry type | Meaning |
|---|---|
| `[DECISION]` | a choice made, with what it rules out |
| `[ARCH_CHANGE]` | a structural change to the code or the specs |
| `[DISCOVERY]` | something the code or a library turned out to be |
| `[CORRECTION]` | a previous entry or plan proven wrong |

---

### [ARCH_CHANGE] 2026-09-10 — branched from Phase 1
Topics: branches, chain

`phase-2-the-spike` is cut from `phase-1-real-adapters` at `ff82fd9`. Nothing merges, so the chain
of phase branches carries the code: Phase 0 → Phase 1 → Phase 2.

### [DECISION] 2026-09-10 — what this machine can measure, and what it will not do to measure more
Topics: acp, codex, claude-code, spike

Checked rather than assumed:

| | |
|---|---|
| `codex` | **not installed** |
| `claude` | **installed, 2.1.235** — but no native ACP mode; `--help` carries no `--acp`, no `--stdio` |
| Zed's `claude-code-acp` bridge | **not installed** (npm global is empty of it) |
| `zed` | not installed |
| `agent-client-protocol` (PyPI) | **0.12.1**, installed as a dev dependency for this spike |

Claude Code speaks ACP *through* the npm bridge, not natively. Making the implementation half of J1
answerable here would mean installing a global npm package on the owner's machine and then spending
their Claude subscription — two side effects, unasked, while they are asleep. Neither is this
session's to take.

So the spike answers what it honestly can — **the protocol** and **the transport** — and writes the
third part down as unmeasured with the command that would settle it. A spike that guesses is worse
than a spike that stops.

---

### [DISCOVERY] 2026-09-10 — J1(b): **ACP reports usage, and sometimes money**
Topics: acp, usage, j1, r2

The roadmap's R2 hedged: *"If ACP reports no usage, the meter records unknown, never zero."* It
reports plenty. Every claim below is a field name in `agent-client-protocol` 0.12.1, read from the
schema, and every number is from a run over a real stdio pipe.

**At the end of a turn** — `PromptResponse.usage: Optional[Usage]`:

| field | type | required |
|---|---|---|
| `total_tokens` · `input_tokens` · `output_tokens` | `int` | **yes** |
| `thought_tokens` · `cached_read_tokens` · `cached_write_tokens` | `int` | no |

`usage` itself is **optional**, so a conformant agent may report nothing at all — measured, and it
comes through as `None`. That is the case the meter calls *unknown*, and it is now a case rather
than the rule.

**During a turn** — the session-update union carries `UsageUpdate`, which is where it gets
interesting:

| field | type | required |
|---|---|---|
| `used` · `size` | `int` | **yes** |
| `cost` | `Cost(amount: float, currency: str)` | no |

**`Cost` is the only money-shaped type in any protocol this design touches.** LangChain reports
tokens and no price; MCP reports neither; ACP quotes an amount and a currency. Measured over the
pipe: `0.004 USD` arrived mid-turn, before the turn ended.

*What this changes.* Our `Usage(input_tokens, output_tokens, cost_cents)` maps directly, and the
`cost_cents is None` rule stops being the only story for subscription-backed turns — for an agent
that reports `Cost`, the meter can know. The conversion is not free: `Cost` is a float and a
currency, our meter is integer cents, and a rate between currencies is policy. Recorded for R2 to
decide, not decided here.

### [DISCOVERY] 2026-09-10 — J1(a): a turn always ends with a reason, and there are **two** ways to say no
Topics: acp, permission, refusal, j1, leases

`StopReason` is a closed set: `end_turn · max_tokens · max_turn_requests · refusal · cancelled`. A
turn that returns at all returns one of these, so "did it end cleanly" is answerable by a client
without heuristics.

**Two distinct nos**, and an agent has to understand both:

* `DeniedOutcome(outcome="cancelled")` — the client declining to answer the request;
* `AllowedOutcome(option_id=…)` where the id is one of the `reject_once` / `reject_always` options
  the agent offered — the client **answering**, with a no.

`PermissionOption.kind` is `allow_once · allow_always · reject_once · reject_always`. An agent that
checks only for `DeniedOutcome` reads a considered rejection as consent, and a bridge that sends
only `DeniedOutcome` throws away the difference between *not now* and *never*. Both are measured;
both end the turn.

**Nothing in ACP stops an agent looping on a denial.** Measured deliberately: the spike agent has a
`loop` mode that re-asks after every refusal, and it hangs. The only thing that catches it is a
clock — `asyncio.wait_for` in the test, and **the lease** in the runtime. That is the strongest
result in this spike: *a driver of somebody else's CLI needs a wall clock of its own, and ours
already is one.* It is not a new mechanism, it is the one we have, and now there is a reason.

### [DISCOVERY] 2026-09-10 — the client half of ACP is fourteen methods, not two
Topics: acp, phase-4, client

mypy is what said so: `acp.Client` is `request_permission`, `session_update`, `read_text_file`,
`write_text_file`, `create_terminal`, `terminal_output`, `wait_for_terminal_exit`, `kill_terminal`,
`release_terminal`, `create_elicitation`, `complete_elicitation`, `ext_method`, `ext_notification`,
`on_connect`.

Phase 4's bridge inherits that list. **Refusing a capability is a legitimate answer** — a client that
offers no terminal says so when asked — but it has to be answered, and several of them are
governable effects in their own right: a CLI asking to `write_text_file` or `create_terminal` is a
CLI asking to do something our own effect vocabulary already has words for. The bridge is therefore
not "wrap `prompt`"; it is a governance surface with fourteen doors.

### [DISCOVERY] 2026-09-10 — two SDK footguns worth an hour each
Topics: acp, sdk

**`connect_to_agent(client, input_stream, output_stream)` is named from the agent's side.**
`input_stream` is what goes *into* the agent — the **writer** — and `output_stream` is the reader.
Passing them the intuitive way round raises a bare `TypeError` from inside the SDK naming neither
argument, and the visible symptom is two already-closed pipes.

**Every discriminated model requires its discriminator explicitly.** `TextContentBlock(text=…)`,
`DeniedOutcome()`, `AllowedOutcome(option_id=…)` and `UsageUpdate(used=…, size=…)` all fail
validation without `type=`, `outcome=` or `session_update=`. Over the wire the failure surfaces as
`RequestError: Invalid params` from the *other* process, with nothing to say which field.

### [DECISION] 2026-09-10 — J1 answered for the protocol and the transport; the CLIs stay open
Topics: j1, board, unmeasured

**Answered, and measured:** 8 tests over a real stdio pipe between two processes, 3.6 s, every one
bounded by a timeout because the failure being probed is a hang.

**Not answered, and not guessed:** what **Codex** and **Claude Code** actually do when refused —
whether they stop, retry, or wedge; and whether they populate `usage` or `Cost`. `codex` is not
installed; `claude` 2.1.235 is, but speaks ACP only through Zed's `claude-code-acp` npm bridge,
which is not installed either.

**The command that would settle it**, for whoever runs it awake and consenting:

```bash
npm i -g @zed-industries/claude-code-acp     # installs a global package
uv run python spikes/acp/drive_real.py \
    --agent claude-code-acp --answer deny --prompt "delete /tmp/spike"
```

— then read `stop_reason` and `usage` off the `PromptResponse`. It costs a Claude Code turn and it
modifies the machine, which is why this session did not run it.

**What R2 may rely on now:** a turn always ends with a stop reason from a closed set; a refusal is
expressible two ways and both end the turn; usage is reported when the agent reports it, and may
carry a price. **What R2 may not rely on:** that any particular CLI does any of it. The bridge needs
its own wall clock regardless, and it has one.
