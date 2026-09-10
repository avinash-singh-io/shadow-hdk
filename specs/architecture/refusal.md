---
type: Architecture
---

# Refusal — what happens when the answer is no

> Researched 2026-09-10 across shipped agent systems, both protocols, and the published literature.
> Commissioned because the owner reframed J1 from *what does a coding CLI do when refused* to the
> generic question: **this harness serves any agent, so what does refusal look like anywhere?**

Governance is the design's centre, and a governance layer that can say no is only as good as what
happens next. This is what the rest of the world does, what that implies for us, and where we stand.

## The two hard constraints

**1. You cannot simply not answer.** Anthropic, OpenAI and Google all reject a request whose tool
calls are not each paired with a result. A refusal must *synthesise* an answer — this is not a design
preference, it is the provider APIs. Missing that pairing is the most commonly filed bug in approval
implementations, with open issues against four separate projects, and it happens because the
*interface* denial state and the *provider message* lowering are two different things and the bug
lives in the lowering.

**2. The error channel means "try again".** MCP defines its error flag as the bucket for *"actionable
feedback that language models can use to self-correct and retry with adjusted parameters"*, and
Anthropic documents the model retrying two or three times on an invalid call. A refusal delivered
there is delivered through a channel whose documented contract is *try something slightly different*
— which is the opposite of what a policy decision means.

## Where the field stands

Most systems collapse *you may not* into *it broke*. Of everything surveyed, three keep them apart,
and only one keeps them apart **on the wire**:

| system | how a denial reaches the model | separate from failure? |
|---|---|---|
| **Pydantic AI** | an ordinary tool return carrying `outcome='denied'` | **yes, structurally** — only `'failed'` maps to the provider's native error flag |
| Claude Agent SDK | a tool result carrying the deny message | yes, by type, at the SDK boundary |
| Strands | a tool result prefixed `DENIED:` | in the policy layer; flattened to `status: "error"` on the wire |
| LangChain, OpenAI Agents SDK, Google ADK, CrewAI, AutoGen, smolagents, LlamaIndex, Gemini CLI, Codex, Cline, opencode | an error-shaped result whose *text* says it was refused | no |

Pydantic AI's own note is the clearest statement of the principle anyone has written down: *a denial
is a deliberate policy decision rather than a runtime error*, so it is sent as an ordinary result
whose content tells the model what happened **without suggesting a transient tool failure**.

**The clearest demonstration of what the missing field costs** is a framework that recovers *this
was a policy denial, not a crash* by **substring-matching its own exception text** — and then uses
what it recovered only to print a hint to the human console. The model, which is the one that has to
change its behaviour, gets the undifferentiated error. The knowledge existed; there was nowhere to
put it.

The worst case found is instructive: one framework encodes a human's "no" as an exit code of 1 — the
value a crashing process produces — and then feeds it to a retry prompt that tells the model *"the
most recent code execution resulted in an error"*. Another marks rejected calls as `completed`, and
its own bug report records the model then hallucinating that the rejected action had succeeded.

## Neither protocol specifies it

**MCP** mandates deniability — *"there SHOULD always be a human in the loop with the ability to deny
tool invocations"* — and defines **no wire representation for a denial**. Its taxonomy has two
buckets, malformed and execution-failed, and neither is *refused*. A tool-scope proposal was closed
as not planned. Its authorization answer is to *hide* the tool rather than refuse the call.

**ACP** has no `denied` outcome and no `denied` status; a refused call must be reported as `failed`.
Its `refusal` stop reason means the **agent** refused, not the policy — do not conflate them.

Notably, MCP's *elicitation* primitive already has the vocabulary tools lack: `accept` / `decline` /
`cancel`, distinguishing an explicit no from an abandoned dialog, and prescribing different handling
for each. The distinction exists one primitive over.

**So there is no spec to conform to here — only two to stay compatible with.** Since this harness
governs *effects* rather than tool names, refusal is the design's genuinely novel surface.

## Where we already stood, and the one thing that was wrong

The kernel has had the right shape since Phase 0, and the research says it is the better shape:

- `Refused` and `Failed` are **separate observations**, not one type with a flag
- a refusal emits its **own event kind**, so the record distinguishes them without parsing text
- governance returns `Allow | Ask | Refuse` — the three-valued decision that four independent
  systems and two papers converged on separately, and that every measured binary allow/block design
  regrets
- what the policy would refuse is **absent** from the catalogue rather than greyed out (`09` §4),
  which is the same two-layer defence the best-designed systems ship

**What was wrong:** the agent adapter collected only `observed` events when mapping results back to
the model, and a refusal emits `refused` and no `observed`. So a refused tool call reached the model
as *"that step did not run"* — no reason, and indistinguishable from a step that never happened. The
governance decision reached the record and never reached the model. Fixed in Phase 9, with tests
pinning all three properties: the call is answered, the reason is carried, and it does not read like
a breakage.

## What the evidence says to do, beyond what we have

Recorded as findings rather than decisions; each would be its own change.

1. **Name the substitute, not just the prohibition.** The strongest measured result in the survey is
   that an agent blocked without a diagnosis mostly fails because it *cannot identify what blocked
   it* — supplying that recovers most of the lost task success, while adding compute does not. The
   one vendor recommendation on phrasing leads with the alternative action rather than the refusal.
2. **Prohibition text alone does not hold.** Across several independent studies, instructing a model
   not to do something reduces but never eliminates the behaviour, and one large trial found models
   working around an explicit instruction up to 97% of the time. A structured refusal is necessary
   and demonstrably not sufficient; the bound has to be structural, which for us is the lease.
3. **An incomplete task is what drives working around a refusal.** This suggests a refusal should
   *close* the goal or offer a legitimate exit, rather than leave the model holding an open task it
   cannot complete. We have `done` with a `gave_up` reason, which is that exit — worth making
   explicit in the shipped role files.
4. **Ship a shadow mode.** Two independent vendors say the same thing: the first version of any
   policy denies things nobody meant to deny. An observe-only governance decorator is cheap.
5. **A denial is an oracle.** One paper documents probing a policy through denial feedback and
   exfiltrating what was learned. Being specific about *what to do instead* while staying
   non-specific about *what exists and why it is protected* is the resolution the evidence supports.

## What could not be established

- No benchmark measures **recovery from a refusal**. Every agent-security benchmark found measures
  whether the agent does the forbidden thing, never how well it recovers from being stopped.
- **Whether stating a reason improves compliance** has never been isolated from stating an
  alternative. The evidence hints the alternative carries most of the effect. This is a hypothesis.
- The rate at which an agent repeats an *identical* refused call is unmeasured anywhere — and is
  computable from our own event stream, since a refusal is its own event kind.

The eval that would settle all three: hold the task and the policy fixed, vary only the refusal text
across bare / with-reason / with-alternative / both, and score repeat-call rate, workaround rate and
correct-escalation rate. It does not exist in the literature and we are unusually well placed to run
it, because our record already distinguishes a refusal from a failure without parsing prose.
