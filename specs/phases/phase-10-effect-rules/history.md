---
type: History
phase: 10-effect-rules
---

# Phase 10 — history

Append only. Newest at the bottom.

### [DECISION] 2026-09-10 — D23: a rule selects by name, never by predicate
Topics: governance, effect-rules, selectors, d23
Affects-phases: none
Affects-specs: specs/architecture/decisions.md

A rule has to say when it applies, and the obvious answer — a condition on the principal, an
attribute, the hour — is the wrong one.

`09` §2 already refuses this shape one level down: the effect vocabulary may grow, but a new field
must be a scope-set or a boolean, something with a natural narrower-than order, because *a
free-form predicate turns a proof into a linter*. The selector inherits the argument. Two rule sets
can be compared — *does this one only narrow that one?* — only if what they say is comparable, and
deciding whether one condition implies another is undecidable in general and unreadable in
practice. The moment a rule set cannot be compared, "refuse a team rule that widens" stops being
arithmetic and becomes somebody's opinion.

So a rule carries `applies_to`, a set of names, empty meaning always. The **host** decides which
names are in play, from its own ladder and its own tenancy, and hands them in. The conditionality
lives on the host's side of the port, where it belongs.

*Rejected:* a `when` expression in any language — it buys conditionality and costs the proof.
*Rejected:* first-match-wins ordering, because order is a hidden operator: two sets with the same
rows in different orders mean different things, and neither the check nor a reader can see it.
Every applicable row applies, and they intersect.

*Overturned by:* a rule that must see the **effects** to know whether it applies. That is a
different shape and deserves its own decision rather than a `when` field nobody argued about.

### [DECISION] 2026-09-10 — D24: the check runs on the rules, not on the run
Topics: governance, narrowing, r5, d24
Affects-phases: none
Affects-specs: specs/architecture/decisions.md

`EffectProfile.narrows` answers *may this step proceed*. R5 asks something earlier: **may this rule
set exist**, given what it was handed.

A team's rules are checked against the constitution's once, when they are loaded, and a set that
widens anywhere is refused with the row and the field that did it. Stronger than catching it per
step, and cheaper: a rule that could never be reached is still wrong, and a run that never happens
to touch it never proves anything.

It is a library function rather than a method, because two callers need it that are not each other
— the loader refusing a bad file, and a host validating rules a person typed into a form before it
stores them.

---

### [ARCH_CHANGE] 2026-09-10 — the engine: rows, the check, and files
Topics: governance, effect-rules, rows, widens, rule-files, r5
Affects-phases: none
Affects-specs: specs/architecture/adapters.md

`Rule`, `RuleSet`, `RuleGovernance` in `adapters/modes`; `widens()` as a library function; `load_rules()`
with a shipped example. A `Mode` is the one-row case and `layer` still works. R5's three claims are
each pinned: rows intersect and only narrow; a set that widens is refused at load naming rule and
field; a refusal at run time names the rule.

### [DISCOVERY] 2026-09-10 — fail-closed was open at N=0
Topics: governance, empty-set, mutation-check, safety
Affects-phases: none
Affects-specs: none

A mutation making an empty intersection permit everything survived, so I wrote the test — and the
test failed against the **unmutated** code. Governance over an empty rule set returned `Allow` for
a harmless step. The refusal logic looked for a *row* that refused, found none, and let the step
through. A rule file that failed to load, or a selection that matched nothing, would have granted
everything and said nothing.

The fix checks the composed ceiling first, and a set that grants nothing now refuses with *no rule
is in force here, so nothing is permitted*. Recorded because the mutation did not find a test gap;
it found the one place the design's central promise did not hold.

### [DISCOVERY] 2026-09-10 — a guard for the seventh field
Topics: effects, vocabulary, d22
Affects-phases: none
Affects-specs: none

`09` §2 says the vocabulary may grow and D22 says the port set is open, so a seventh effect field
is expected rather than hypothetical. A check that silently ignored one would keep passing while
permitting whatever it allows — the worst way for a safety check to fail. Two tests now hold the
line: `FIELDS` must equal the kernel's dataclass fields, and each named field must actually be
compared.

---
