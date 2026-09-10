---
type: History
phase: 1-real-adapters
---

# Phase 1 — history

Append-only. Newest at the bottom.

| Entry type | Meaning |
|---|---|
| `[DECISION]` | a choice made, with what it rules out |
| `[ARCH_CHANGE]` | a structural change to the code or the specs |
| `[DISCOVERY]` | something the code or a library turned out to be |
| `[CORRECTION]` | a previous entry or plan proven wrong |

---

### [ARCH_CHANGE] 2026-09-10 — branched from Phase 0, because nothing merges
Topics: branches, chain
Affects-specs: specs/phases/phase-1-real-adapters/overview.md

`phase-1-real-adapters` is cut from `phase-0-the-runtime` at `0e39c70`, not from `staging`. Nothing
merges without the owner, so the chain of phase branches is what carries the code forward: Phase 2
will branch from this one, and so on until the owner lands the lot. Each phase's `history.md` records
its parent, so the chain is readable without `git log --graph`.

### [DECISION] 2026-09-10 — what this machine can really test, and what it must not
Topics: providers, ollama, api-keys, live-tests

Measured before planning rather than assumed:

| | |
|---|---|
| `ollama` binary | installed, **not serving** — started locally for this phase |
| a model on disk | **`gemma4`**, already pulled — so a live check costs no download |
| `langchain-core` | 1.6.2, present transitively through langgraph |
| `langchain` | **absent** — `init_chat_model` lives there, so the adapter depends on it |
| `mcp` SDK | **absent** — the adapter depends on it |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | **both set in the environment** |

**The keys are set and the suite will not use them.** Spending someone's money is not a decision a
test suite gets to make, and the owner is asleep. Live tests run against **local Ollama only**;
OpenAI, Anthropic and HuggingFace are exercised through a fake `BaseChatModel` that satisfies
langchain's own interface — which is the right test anyway, because what is being tested is *our
translation*, not their servers.

Nothing is downloaded either. A model that is not already on disk is a multi-gigabyte fetch on
someone else's machine overnight, so `gemma4` is what the live check uses because `gemma4` is what
is there.

### [DECISION] 2026-09-10 — D14: a port may grow a method, with a default
Topics: ports, streaming, contracts, d9, d14
Affects-specs: specs/architecture/decisions.md

`09` §3 says a **port** is added with a refuse-not-crash default. It does not say what happens when
an existing port grows a **method**, which is what `stream` is. The same rule, one level down:

> A method added to a port ships with a default implementation on a mixin the adapter can inherit.
> An adapter that ignores it keeps working; one that can do better overrides it.

For `stream`, the default calls `complete` and yields a single chunk carrying the whole response.
That is honest — a non-streaming provider genuinely produces its answer all at once — and it means
the five adapters written in Phase 0 need no edit.

By D9 this is still a **contract change**: every package takes a minor bump together, and it earns a
row under *Pins* on the board, because the join with the product lane is the only place two lanes
can break each other.

---

### [CORRECTION] 2026-09-10 — the owner supplied a HuggingFace token; live checks moved off Ollama
Topics: providers, huggingface, secrets, live-tests

The plan said local Ollama. Mid-phase the owner supplied `INTENT_HF_TOKEN` and
`deepseek-ai/DeepSeek-V4-Flash:deepinfra`, and asked for HuggingFace instead. Done — and it is the
better test anyway: HF Inference Providers is **OpenAI-compatible**, so the live path now exercises
the same code as OpenAI, Together, Groq, vLLM and most self-hosted servers, rather than one vendor's
own client.

**The token is not in this repository and will not be.** It lives in a `0600` file in the session
scratchpad, outside the worktree; code and specs name only the *variable*. A sweep for
`hf_[A-Za-z0-9]{20,}` runs over everything before each commit of this phase.

The Ollama server this session started was stopped; nothing was downloaded.

**Live tests are deselected by default** — `addopts = "-m 'not live'"` — because they cost money and
a suite should not decide to spend someone's. `uv run pytest -m live` opts in. CI has no token and
runs the fake path.

### [ARCH_CHANGE] 2026-09-10 — Groups 0 and 1: the port grew a method, and one adapter reaches every provider
Topics: streaming, modelport, langchain, usage, pricing, g0, g1

**D14 in practice.** `ModelPort.stream` ships with a default on the protocol body: call `complete`,
yield the whole answer as one chunk. Every adapter written in Phase 0 needed no edit, and the
default is *honest rather than pretend* — a provider that answers all at once really does produce
one chunk, and chopping it into fake deltas would make a run look like it streamed when it did not.
By D9 this is a contract change, so all five packages moved to **0.2.0** together.

**One adapter, every provider.** `LangChainModel` over `init_chat_model`, with vendors as optional
extras so the base install pulls no SDK. What the file actually *is* is a translation — messages,
tool schemas, tool calls, usage, both ways — and that is what the fake tests exercise.

**Tokens are the provider's fact; money is the product's.** No provider reports cents, and the
harness holds no rate card: a rate card is policy about *this tenant's contract*, which `09` §8 puts
on the other side of the boundary. So `cost_cents` is `None` — *unknown* — unless a host supplies a
`price` callback, and the meter then says it cannot total rather than adding zero. Asserted on the
real wire: HF reports `input_tokens`/`output_tokens` and no price at all.

**Measured, live, against `deepseek-ai/DeepSeek-V4-Flash:deepinfra`:** text returns; usage reports
10 input / 4 output tokens and `cost_cents: None`; a tool call round-trips with its id and arguments;
a stream arrives and concatenates to the answer. 4 live tests, 4 passed.

### [DISCOVERY] 2026-09-10 — a real stream is mostly empty frames, and a test asserted the provider
Topics: streaming, live-tests, mutation-check

The first live streaming test asserted `len(chunks) > 2` and failed. **The measurement said the
assertion was wrong, not the code**: over this route the model sends five frames of which exactly
one carries words. So the faithful translation is one text chunk plus a final one, and a test that
demands a provider stream token-by-token is testing somebody else's server. Rewritten to assert what
the *adapter* guarantees; multi-chunk streaming is proven against the fake, where the deltas are
ours to choose.

The empty frames are dropped rather than passed on — four empty deltas in the record would make a
run look like it streamed. A mutation that stopped filtering them **left the suite green**, because
the fake had been too tidy to produce any; the only test covering it was the live one, which a
normal run deselects. That is the fourth vacuous test a mutation check has found, and the fix was
again a better test: a fake that sends what the real provider sends.

### [DISCOVERY] 2026-09-10 — a stale `__pycache__` made a mutation look like a defect
Topics: mutation-check, tooling

After restoring a mutated file, the suite still failed and the source on disk was demonstrably
correct — `inspect.getsource` at run time showed the right code. Inserting a `print` made it pass,
which is the signature of a stale bytecode cache rather than a bug: the restore-by-copy and the
`.pyc` disagreed. **The mutation harness now clears `__pycache__` after every restore.** Half an
hour spent because a tool lied, and worth the entry so the next occurrence costs a minute.

Also fixed while here: `aclosing` around the provider's generator, so the HTTP stream under it
closes the moment we stop reading. It removed a real teardown error from httpcore2 that appeared on
every live streaming call.

---

### [ARCH_CHANGE] 2026-09-10 — Group 3: a mode is a ceiling and an ask line
Topics: modes, governance, layering, meet, g3

`Mode(name, ceiling, ask_above)` and `ModeGovernance(modes, default, key)`. Two modes, ten, or one
called `auto` is a different **mapping**, not different code — the runtime knows no mode names, and
this adapter knows only the ones a product hands it. The four in the tests (`read`, `build`, `act`,
`auto`) are examples, not a vocabulary the adapter imposes.

**An unknown mode refuses and says which name it did not recognise.** The dangerous failure here is
silent widening: a typo in a mode name resolving to whatever the default happens to be. A mutation
that made it fall back to the default fails the suite.

**`ask_above=None` means never ask** — a thing a product may legitimately want, and the adapter will
not second-guess it, but it has to be *said* rather than inherited from a neighbouring mode.

**A layer can only narrow, and that is arithmetic.** `layer(base, over)` is `EffectProfile.meet`,
which the kernel already property-tests as a greatest lower bound, so "a team may tighten what it
was given and never loosen it" is not a review comment. A hypothesis property asserts it over
arbitrary profiles, and a mutation that takes the layer's ceiling instead of the meet fails.

When a step is asked about, the question **names the field that crossed the line** — reads more than
usual, reaches outside, is irreversible — so a person being asked is told what they are answering.

Five mutations, all failing. The mutation harness now clears `__pycache__` after each restore.

---

### [ARCH_CHANGE] 2026-09-10 — Group 2: an MCP server's tools become components
Topics: mcp, annotations, effects, assume-worst, g2

`McpComponents` over the official SDK's stdio client, tested against a **real MCP server run as a
subprocess** — `tests/adapters/mcp/server.py`. A seam tested against a stand-in for the other side
is a seam tested against your own idea of it, and this is the seam most components will arrive
through.

**The interesting part is not the plumbing.** MCP's annotations cover about half our six fields, and
the adapter derives what it can and hardens the rest. Measured against the real server:

| tool | declares | comes out as |
|---|---|---|
| `look_up` | read-only, closed-world | writes nothing, reaches nothing, reversible — **and still uncontained and costly**, because a server saying it only reads has said nothing about where it runs |
| `wipe` | destructive | irreversible |
| `append` | not read-only, **not** destructive | writes, reversible |
| `mystery` | **nothing at all** | `ASSUME_WORST` |

The last row is the property the open registry rests on, and it is governed end to end: a `read`
mode allows `look_up` and refuses `mystery` and `wipe`, and nobody had to know those tools existed.
That is the whole argument for governing effects rather than names.

### [DISCOVERY] 2026-09-10 — a session belongs to the task that opened it
Topics: mcp, anyio, tests

The contract suite's `port()` is synchronous, so the first version started the server in an autouse
async fixture. Every inherited test errored: *"Attempted to exit cancel scope in a different task
than it was entered in"* — anyio refusing, correctly, to let a session cross tasks.

Rather than work around it, it is written down: **an `McpComponents` belongs to whoever entered
it.** `ComponentPortContract` gained a `using()` hook — an async context manager, defaulting to the
plain `port()` — so an adapter with a lifetime is opened and closed *inside each test*. Ports
without a lifetime are unaffected.

### [CORRECTION] 2026-09-10 — the ceiling was wrong, the arithmetic was right
Topics: modes, contained

The end-to-end mode test failed: a `read` mode refused `look_up`. The mode's ceiling had left
`contained` at its default `True` — *containment required* — and `look_up` is uncontained, because
nothing declared otherwise. The refusal was correct. `contained=False` in a **ceiling** means
*uncontained is permitted*, which is the truthful setting for a laptop with no sandbox.

### [DISCOVERY] 2026-09-10 — two mutations found two missing tests
Topics: mutation-check, mcp

*Dropping the destructive hint left the suite green*, because MCP's default for an unstated
`destructiveHint` is **destructive** — so a tool that omits it and an adapter that ignores it look
identical. The only shape that tells them apart is a tool declaring `destructive_hint=False`, and
the reference server now has one (`append`).

*Narrowing the transport `except` left the suite green*, because every test exercised a server that
answered — even `explode`, which answers with an error result rather than dying. A server is a
process on the other end of a pipe and processes die; there is now a test where the transport raises
mid-call and the agent gets an observation rather than a traceback.

Seven mutations, all failing.

---

### [ARCH_CHANGE] 2026-09-10 — Group 4: the harness on a real model, a real server and a real policy
Topics: examples, live, exit-criteria, g4

`examples/real.py` — the same harness with nothing stubbed. `bare.py` proves the *shape*; this
proves the **seams**: an HTTP wire to a real model, a real MCP server in a subprocess, and a mode
that actually refuses.

**Measured, live:** 7 live tests pass in 34.6 s. 202 offline tests pass with the live ones
deselected. ruff and mypy strict clean over 47 files.

Two things the demo showed that no offline test could.

**The agent fanned out.** Given four turns, a real model asked the server two questions at once —
so `FanOut` and `Send` ran because a model chose them, not because a test built them.

**The mode decided what the model could see.** The reference server publishes `wipe`, `append`,
`mystery` and `explode` beside `look_up`. The `looking` ceiling permits reading only, so the other
four were **absent from the catalogue** rather than refused at call time, and a real model — given
every chance over six turns — never had one to reach for. That is the open registry and
effect-governance meeting on a live wire, and it is asserted rather than admired.

### [DISCOVERY] 2026-09-10 — the first live run failed, and it was the demo's data
Topics: examples, reference-server

The first run spent all six turns guessing spellings — `LATHE-3 mass`, `lathe line 3 weight`,
`lathe 3 weight` — and ended `out_of_turns` having already had the answer in turn three. Nothing in
the harness was wrong: the reference server answered only exact keys, and the record holding the
mass did not hold the measurement date.

That is a **demo-data** problem and it was fixed as one: the server matches forgivingly and each
asset carries one complete record. A reference server that answers only an exact key is not a
reference server, it is a dictionary. The second run answered in **one** lookup, proposed, and
stopped — 51 events became 13.

Worth stating plainly because the temptation was to change the harness: the agent behaved correctly
throughout, and the honest fix was to the thing that was actually wrong.

### [CORRECTION] 2026-09-10 — I committed over a red gate, because `| tail` hid its exit code
Topics: gate, tooling, discipline

`9d08285` was committed with **four mypy errors**. The cause is worth writing down because it will
recur otherwise: the gate was being run as

    uv run ruff check -q && uv run ruff format --check -q && uv run mypy 2>&1|tail -1 && uv run pytest …

and a pipeline's exit status is the **last** command's. `tail` always succeeds, so mypy's failure
was printed and then stepped over, and the `&&` chain carried on to a green-looking pytest. The
output said `Found 4 errors in 1 file` in plain sight and the chain said everything was fine.

Fixed in `0e4d0b1`. The gate is now run so each exit code is read on its own:

    uv run ruff check -q; echo $?
    uv run mypy > out 2>&1; echo $?

The errors themselves were narrowing in the new live test — reading `.output` off an `Observation`
union rather than off a `Completed`. Trivial to fix; the point is that a tool was allowed to lie
about whether the work was done, which is exactly the class of thing the mutation-check discipline
exists to catch, applied to the gate rather than to a test.
