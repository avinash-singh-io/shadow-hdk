---
type: Architecture
---

# The optimiser — a port, specified before it is built (Phase 27, D72)

> Specified so that nothing built before it makes it impossible, and so that the first loop is
> built **after** its evaluator is locked (Rule 11) rather than around it. Nothing here is code.

## What would be optimised

Everything an optimiser could change is already **data** (principle 10, D64, D54): a mode's
`Behaviour` (the system text it appends, the effort, the temperature), a skill's text, a pattern's
role and prompts, a battery's tool descriptions. Each is a document with an id and a source
(shipped · file · store), read live by a registry. An optimiser improves a document and proposes
the improved one; it never edits a running thread.

A **program** is therefore `(kind, id, document, slots)`: which registry, which entry, its
document as it is, and which fields the optimiser may change. Fields not in `slots` are held —
the policy a mode names, the effects a battery vouches for, a skill's description line are not
the optimiser's to touch, because governance reads them.

## The port

```
OptimiserPort.improve(program, evaluator, budget) → Improved

Improved:
    program      the same kind and id, the document rewritten in its slots only
    before       the evaluator's scalar on the document as it was
    after        the evaluator's scalar on the document as rewritten
    trials       how many candidates were scored, and what each cost
    evaluator    the evaluator's version tag — the score is meaningless without it
```

`budget` is a `Budget` (steps · seconds · cents): an optimiser spends inference, and it is charged
to a lease like any run. The optimiser's own effect profile is honest — `costs = true`,
`reaches = true` where the evaluator's turns reach a provider, `writes = {record}` — and the
modes judge it as they judge anything; a confined mode refuses it by its profile.

**The result is a proposal, not an edit.** `Improved` goes through the sink as
`Proposal(kind="optimisation")`, exactly as a minted skill does (D56): the host keeps it or
not; the store row changes when a person or the host's rule says so; the next read sees it (D66).
An optimiser that wrote directly to the registry would be a loop with no gate, which is the
thing this project is against.

## The evaluator, locked first (Rule 11)

An evaluator is `(version, corpus, score)`:

- **`corpus`** — a fixed set of cases, each a brief and what "good" is for it: a turn's expected
  outcome (`completed`), the components that must have been called (and must not), an assertion
  on the workspace after, and — where the product's judgement is the point — a rubric a second,
  frozen model scores. Cases are recorded as the record's own events, so they replay.
- **`score`** — one scalar over the corpus. Not a vector, not a dashboard; a number that goes up
  or does not.
- **`version`** — a tag the scalar carries. Changing the corpus or the scorer is a new version;
  scores across versions are not compared.

Two things make this affordable, and both exist: the **recorded model port**
(`runtime.replay.RecordedModel`, Phase 8) replays a tape of real completions for nothing, so a
corpus scored by key runs with no bill; and a **scripted provider** (the doubles every suite
already uses) scores the runtime's part without a model at all. A corpus that needs a live
subscription is scored rarely and on purpose (`-m live`), never in the loop.

The first evaluator is `v1` in `tests/runtime/test_benchmark.py`'s sibling — committed, tagged,
and never edited; `v2` is a new file. That commit is the precondition for building the port's
first implementation, and the Rule that says so is the one this project will not bend.

## What would sit behind it

**DSPy** (Stanford, MIT licence) is the reference: a *program* is a module with an instruction
and demonstrations, an *optimiser* (`BootstrapFewShot`, `MIPROv2`, `GEPA`) rewrites instructions
and selects demonstrations against a *metric* over a *trainset*, and it is careful about the
same thing Rule 11 is — the metric is fixed while the optimiser runs. The mapping is direct and
needs no new concept on our side:

| ours | DSPy |
|---|---|
| a program's `system` slot | the module's instruction |
| the corpus | the trainset |
| the evaluator's `score` | the metric |
| `Budget` | the optimiser's trial count and the LM's own budget |
| the recorded model port | the LM behind the module, replaying |
| `Improved` through the sink | the compiled program, saved |

It would be one adapter, `adapters/dspy`, importing nothing but the kernel, the runtime and DSPy
(the stands-alone rule), and it would be **consumed** (principle 5): the search is theirs; the
program, the evaluator, the budget and the gate are ours.

A second implementation, `adapters/basic`'s `HillClimb`, is the one to build first if DSPy's
dependency weight is not wanted: propose a candidate per trial by asking a model for one
rewrite of the slot, score it, keep it if better. It is what makes the port's contract suite
runnable without DSPy, which is how every port here gets its contract held (TD-004).

## Not built, and why

Rule 11 first. The corpus does not exist yet — the studio's five scenarios and the coder's live
tests are the raw material, recorded turns and all, but none is a *locked* set with a scalar. The
port is specified here so the file formats an optimiser needs (documents with slots, proposals of
kind `optimisation`, an evaluator version on a score) are settled before a loop is written around
them, and so that the first loop, when it comes, is measured against something that was not
written to make it look good.
