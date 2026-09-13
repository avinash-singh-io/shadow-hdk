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
