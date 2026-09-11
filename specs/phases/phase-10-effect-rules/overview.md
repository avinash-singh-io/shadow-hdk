---
type: Phase
phase: 10
name: effect-rules
epic: 0004-governance-as-rows
status: complete
topics: [governance, effect-rules, rows, intersection, narrowing, mode-files, d23, d24, r5, j4]
deps: [phase-9-the-wire]
---

# Phase 10 — Effect rules

## Goal

`09` §11 names it: **the effect-rules governance engine — rules as rows over effect profiles,
composed by intersection, with the narrowing proof. This is the governance adapter, and it is
generic.**

R5 is what a person sees when it works:

> be told how your team works in plain sentences; **refuse a team rule that widens**; explain any
> setting's value and where it came from.

Three claims, and each can fail on its own.

| | claim |
|---|---|
| rows | a rule is a **row of data**, several rows compose, and the composition can only narrow |
| the check | a rule set that **widens** what it was given is refused — before it runs, not during |
| the account | a refusal names **which rule** and **which field**, because *explain where it came from* is the release criterion |

`adapters/modes` already holds the one-row case: a `Mode` is a ceiling and an ask line, and `layer`
composes exactly two of them. This phase is that generalised to N, made loadable from a file, and
given the check as a library.

## D23 — a rule selects by name, never by predicate

A rule has to say *when it applies*. The obvious answer is a condition — match on the principal,
on an attribute, on a time of day — and it is the wrong one here.

`09` §2 is explicit: the vocabulary may grow, but **a new field must be a scope-set or a boolean**,
something with a natural narrower-than order, so intersection and the narrowing proof still work.
*A free-form predicate is refused, because it is what turns a proof into a linter.* The same logic
governs the selector. Two rule sets can be compared — *does this one only narrow that one?* — only
if what they say is comparable. A predicate is not: deciding whether one condition implies another
is undecidable in general and unreadable in practice, and the moment a rule set cannot be compared,
"refuse a team rule that widens" stops being arithmetic and becomes somebody's opinion.

**So a rule applies by name.** It carries `applies_to`, a set of names; empty means always. The
host decides which names are in play — from its own ladder, its own tenancy, its own hour of the
day — and hands them in as a **selection**. All the interesting conditionality lives on the host's
side of the port, where it belongs, and the rules themselves stay comparable.

*Rejected:* a `when` expression, in any language. It buys conditionality and costs the proof.

*Rejected:* rules ordered by specificity, first match wins. Order is a hidden operator: two rule
sets with the same rows and different order mean different things, and neither the check nor a
reader can see it. **Every applicable row applies, and they intersect.**

*Overturned by:* a host that genuinely cannot decide selection outside the judgement — a rule that
must see the *effects* to know whether it applies. That would be a different shape, and it should
arrive as its own decision rather than as a `when` field nobody argued about.

## D24 — the check runs on the rules, not on the run

`EffectProfile.narrows` already answers *may this step proceed*. What R5 asks for is different and
earlier: **may this rule set exist**, given what it was handed.

A team's rules are checked against the constitution's **once**, when they are loaded, and a set that
widens anywhere is refused with the row and the field that did it. That is a stronger guarantee than
catching it per step, and a cheaper one — a rule that could never be reached is still wrong, and a
run that never happens to touch it never proves anything.

The check is a **library function** rather than a method on a class, because two things need it that
are not each other: the loader, refusing a bad file, and a host, validating rules a person typed
into a form before it stores them.

## What is NOT in this phase

- **Warrants, consent, who may sign.** `09` §8 puts those on the product's side of the seam.
- **The settings ladder.** R5's *explain any setting's value* is Intent Studio's resolver; what the
  harness owes is that a **judgement** can say which rule decided it.
- **A seventh effect field.** D22 says the port set is open and `09` §2 says the vocabulary can grow;
  neither is a reason to grow it today.

## Exit criteria

- Several rules compose by intersection, and the result narrows every one of them
- A rule set that widens what it was given is refused, naming the rule and the field
- A refusal at run time names the rule that refused
- Rules load from a file a team can write, and a bad file is refused by name
- `adapters/modes` keeps working — a `Mode` is the one-row case
