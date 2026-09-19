# `shadow_hdk.adapters.modes`

A mode is **a ceiling and an ask line** — two effect profiles, and nothing else:

```python
READ = Mode("read", EffectProfile(reads=EVERYTHING))
BUILD = Mode("build", EffectProfile(reads=EVERYTHING, writes=ScopeSet.of("workspace")))
ACT = Mode("act", ASSUME_WORST, ask_above=EffectProfile(reads=EVERYTHING, writes=EVERYTHING))
AUTO = Mode("auto", ASSUME_WORST)

ModeGovernance({m.name: m for m in (READ, BUILD, ACT, AUTO)}, default="read")
```

Two modes, ten, or one called `auto` is a different mapping through the same adapter. The runtime
knows no mode names; this adapter knows only the ones a product hands it.

**A team's layer can only narrow**, and that is the kernel's `meet` rather than a review — the
property test says so over arbitrary profiles.

The full rules-as-rows engine, with mode *files* checked in CI, is Phase 10. This is what a product
needs before that exists.

**Plan limits (Phase 36, D109).** `ModeSpec.plan` — depth, fan-out, steps — is what a mode admits;
a document's `[plan]` table inherits the named policy's value on any axis it leaves out and is
refused by name if it widens the policy on any axis (`widens_plan`). `PLAN_OF` holds the shipped
ceilings. `Conversation.plan_limits` meets the host's with the mode's at every turn, so
`set_mode` changes what the next plan may be without a reopen.

**A web read from the serving process, under the shipped modes (0.34, D138).** A battery that
reads the web from the serving process declares `reaches = true, contained = false` — true, and
the shipped policies judge it as they judge anything. `read-only` allows it: look, and look at
the web; it writes nothing a reach could carry out, and a read-only policy has to work over any
environment, a `full` one included, where nothing is proven contained. `workspace-write` — the
silent writing mode — hides it: a reach beside writes is an egress channel. `ask` **asks** before
it: "every write, run or delete inside the workspace is asked about" is its definition, and
Claude Code's default prompts before a fetch the same way (before 0.34 `ask` refused it outright,
which left a served product no door but re-vouching the effect). An `allow` rule for the one tool
then stands in for the person — the door a served product uses:

```toml
# a rules row, or `store/put` on the `rules` collection: search runs without a prompt, in `ask`
[[rule]]
component = "web_search"
decision = "allow"
mode = "ask"
```

`full` allows it as it allows anything. A product that wants its own line hands `ModeGovernance`
a `Mode` of its own (a ceiling and an ask line); a rule never widens a shipped ceiling. Nothing
re-vouches a battery's effects to get past a ceiling: the `ddgs` file says `contained = false`
because that is true. A read that *is* contained — through a proxy with an allowlist (D137) —
narrows every ceiling and needs no door.
