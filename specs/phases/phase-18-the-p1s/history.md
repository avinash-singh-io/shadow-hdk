---
type: History
phase: 18-the-p1s
---

# Phase 18 — history

### [DISCOVERY] 2026-09-10 — five reproductions, before a line was changed
Topics: workspace, leash, containment
Affects-phases: none
Affects-specs: none

Against a temp directory: a hard link let `read_file` return outside content **and `write_file`
overwrite the outside file**; `{"path": "a\0b"}` raised `ValueError` out of `invoke`; a
backgrounded process wrote its marker after the step returned; `HOME` reached the child; and a
five-line fake `runsc` on `PATH` produced *"gvisor proved containment"*. Every one as filed.

---

### [DECISION] 2026-09-10 — D35: a step owns the process tree it starts
Topics: leash, d35, attribution
Affects-phases: none
Affects-specs: specs/architecture/adapters.md

A leashed program gets its own process group and the group is killed when the leash returns,
timeout or not. Rejected: killing only on timeout (which is what let a cleanly-exiting program
leave a process behind), and treating detached children as a feature (the harness's claim is that
every effect is attributed to a step, and a process outliving its step is the counter-example).

---

### [DECISION] 2026-09-10 — D36: containment is proven by what is denied, never by what is announced
Topics: contained, d36, proof
Affects-phases: none
Affects-specs: specs/architecture/adapters.md

`probe()` matched the string `gVisor` in `dmesg` output produced inside the sandbox — it asked the
thing being trusted to vouch for itself. A proof is now a capability test: attempt what a contained
program must not be able to do and prove it failed. What the backend says is kept separately as
`declared` and named as a claim. A backend that cannot be capability-tested does not silently pass;
the deployment must name its trust in an argument. Same shape as BUG-007: a check that looks like a
gate and is not is worse than no check, because `ContainedSandbox` refuses to exist without one.

---

### [NOTE] 2026-09-10 — Group 1: two deadlocks of my own, and four claims nothing could see
Topics: leash, workspace, mutation, deadlock
Affects-phases: none
Affects-specs: specs/architecture/adapters.md

The workspace fix is four lines and a docstring. The leash was not: **the first implementation
deadlocked twice, and its own tests found both.** Reading stdout to its end while stderr fills its
pipe leaves the child blocked on a write nobody drains. And *stopping* reading at the cap — the
obvious way to bound memory — leaves a paused pipe that never reports EOF, so the process can
never be reaped: the step hung until the test runner gave up, with the child already dead. Both
streams are read at once now, the overflow is drained and discarded, and the tree ends the moment
a cap is reached.

`preexec_fn` was the other wrong turn. It runs between fork and exec in a process that has threads,
and on the one platform that refuses `RLIMIT_AS` its failure surfaced as *Exception occurred in
preexec_fn* — taking the whole step with it. The limit is set from the parent with `prlimit`
instead, which exists only where the limit does. A probe that measured the platform by setting a
limit on **this** process and putting the old one back could not put it back, so
`MEMORY_LIMIT_ENFORCED` is a plain statement and `adapters.md` says the same.

Fifteen mutations, four survivors, each a claim nothing could see: ending the tree at the cap
bounds *time*, not output; reading both streams at once was masked by that same kill, so its test
runs with no cap in play; the memory limit skips on macOS, so what is asserted everywhere is that
the leash *asks*, with the child's pid; and collecting only to the cap is invisible in the output —
identical text either way — so it is measured with `tracemalloc`, where twenty megabytes of output
must not become twenty megabytes of memory.

---

### [NOTE] 2026-09-10 — Group 2: the two lines the mutation pass drew
Topics: contained, d36, proof, mutation
Affects-phases: none
Affects-specs: specs/architecture/adapters.md

The fix is small; the two distinctions inside it are the point, and both came out of mutations that
survived a first pass.

**Inconclusive is not a denial.** A probe that fails to *start* also fails to connect, so a check
looking only for the absence of success certifies every backend that can run nothing — which is how
the original bug would have come back wearing a capability test's clothes. The probe therefore says
`DENIED` or `REACHED`, and silence is `Inconclusive`.

**Trust covers an unknown, never a fact.** `trusting_the_backend_without_proof` is for a check that
could not run. A backend that *ran* the check and reached the host is refused however much the
operator trusts it: an operator may sign for something nobody could establish, not for something
established against them. Nothing tested that combination until a mutation asked.

Also worth recording: the reproduction was re-run against the fix rather than assumed. The fake
`runsc` still announces *Starting gVisor...* — `declares()` returns it — and `ContainedSandbox`
now refuses it, naming the capability it failed to deny.

---

### [DECISION] 2026-09-10 — D37: a parent that parks comes back holding its children
Topics: children, resume, durability, d37
Affects-phases: none
Affects-specs: specs/architecture/runtime.md

Four of a `HeldChild`'s six fields are JSON and ride in `RunState.children`. The other two are
objects and were dealt with rather than wished away. The **checkpointer**: a child now shares its
parent's by default instead of getting a private `InMemorySaver` — a child that must outlive its
parent's park has to share its parent's durability, and a private saver never could. The
**cancellation**: a fresh one, because nothing a run is still holding had been cancelled, or it
would not still be held. A child spawned with a checkpointer of its own is named in
`children.lost`, with the reason, so a parent can tell *this child is gone* from *I never had
one* — the distinction whose absence made it quietly spawn a second child.

Rejected: inventing a checkpointer for an unreachable child (a handle that answers nothing);
keeping the registry in memory and hoping the parent never parks (an Ask is the ordinary pause);
and dropping the child silently, which is the bug.

---

### [NOTE] 2026-09-10 — Group 3: four survivors were the tests looking in the wrong place
Topics: children, mutation, testing
Affects-phases: none
Affects-specs: none

Fourteen mutations, five survivors, and only one was about the code. Reporting a lost child could
not be told from restoring it, because the parent only counted its spawns. The headstone tests
released the child *after* the pause, where the record never says *held* — the only arrangement in
which a headstone matters is a release **before** the park. Asserting the end state proved nothing,
because a resurrected child was simply released a second time and the hand was empty again by the
time anyone looked; what is asserted now is what the parent held **on entry** to the resumed step.
And a child that *ended on a send* needs the same headstone as one released, which nothing covered.

The fifth is **equivalent**: not re-recording a released handle at restore changes nothing, because
the checkpoint already carries the `None` and `merge_dicts` keeps it across every later leg.

---

### [DECISION] 2026-09-10 — D38: a parked step resumes where it parked — in progress, not from the top
Topics: resume, interrupt, governance, consent, d38
Affects-phases: none
Affects-specs: specs/architecture/runtime.md

LangGraph re-runs a node from the top on resume, and `interrupt()` returns the answer only where it
was raised. Everything above it therefore happened twice, and the runtime treated the second pass as
if it were the first: it judged again, and it invoked again.

Judging again is the serious half. A policy that changed its mind while a human was thinking
**overruled the human it had asked** — and a policy that stopped asking discarded a refusal and ran
the work. Consent before effect is the entire reason an Ask exists; a re-judge that can overturn the
answer makes the pause theatre. So a step the checkpoint says parked is **not judged again**, and an
`Await` is **not invoked again** — it already said `Pending`, and what it is waiting for is the
answer, not another call.

`_stream` already read the checkpoint's pending interrupts to rebuild D33's `resume_seq`; it now
reads all of them and hands the resumed leg a map of step id to what that step parked on. That map
is consumed on first use, so a step that parks a second time parks properly rather than resuming
into a stale record.

**The answer is a `Judgement`.** A bare string used to be ignored, because the re-judge was really
deciding; now that the answer decides, it has to be one — `Allow()` or `Refuse(reason)` in process,
its JSON over the wire, loaded at the runtime's edge like everything else that crosses (D19).
Anything else is refused, because a value nobody can read as consent must not be treated as consent.

One answer settles every step parked in the same superstep, which is what a `FanOut` of two Asks
needs; an answer keyed by step id addresses them one at a time.

Rejected: **replaying the node and suppressing the second effect** (a ledger of what already ran —
more state to keep correct across a park than the interrupt record already is, and it still re-asks
the policy); **re-judging but preferring the human's answer on conflict** (the policy is then asked
a question whose answer is discarded, which is worse than not asking); and **an idempotency key on
every irreversible invocation**, which the audit's row proposed. The key is real and stays where it
is — a device or a network retries on its own — but it makes a double act survivable rather than
absent, and here the harness was manufacturing the double itself. Fix the cause.

*Overturned by:* a LangGraph that resumes a node in place, which would make the record redundant.

---

### [NOTE] 2026-09-10 — Group 4: five tests encoded the bug they were meant to catch
Topics: testing, resume, mutation, honesty
Affects-phases: none
Affects-specs: none

The audit found this bug by reading; the suite had 771 tests over the same code and was green. Worth
naming why, because it is the same failure four times.

`test_await.py` asserted **one `Observed`** where the claim was one *invocation* — and `Observed` is
emitted once no matter how many times the component ran. `test_acting.py::test_a_retry_carries_the_
same_key` asserted `["r-1/s1", "r-1/s1", "r-1/s2"]` and its docstring explained the repeated key as
the feature that makes the double act safe: the test **documented the bug as a design**. Three more
answered an Ask with the bare string `"yes"` and passed, which could only work because the answer
was being ignored — the re-judge decided, and the string never had to mean anything.

So the fix broke five tests, and every one of them broke because it was wrong. Each was rewritten
from the corrected premise rather than adjusted until it passed.

**The audit's own row was also wrong**, in the run's favour: it said two Asks in one `FanOut` end
the run `failed` with LangGraph's message. Reproducing it showed the run parks again and a caller
can answer both one at a time, re-running the answered branch each time. Worse than it sounds in one
way — silent re-running rather than a loud failure — and the backlog row now says so.

Twelve mutations, all twelve bite. Two needed the right command and the right test before they did:
loading a judgement from JSON only bites when the wire suite is in the run, and *resumes every time*
rather than *once* only bites with a resume inside an `Until` loop, which nothing had covered.

---

### [NOTE] 2026-09-10 — Group 5: a docstring that argued for the fix, and a docstring that was the bug
Topics: acp, meter, money, testing
Affects-phases: none
Affects-specs: none

`Spend`'s own docstring made the argument that the bug defeated. It says money accumulates as
`Decimal` and is converted **once**, because *converting per call would round 0.004 USD to zero and
a thousand such calls would still be zero. Two hundred of them are eighty cents, and that is what
the meter is told.* The class was right. The one place it was read handed the meter the running
total instead of the difference, so `step.py` charged the first turn again on the second and twice
more on the third — and the sub-cent care was spent to produce a number nobody used correctly.

Two hundred charges of $0.004 is a test now, and it is the docstring's own sentence.

**The row's proposed fix was rejected, and this is why.** It said `None` below a cent. `None` is
*unknown*, and a meter charges nothing for unknown — so the money would have been lost exactly as
before, relabelled. The fix that keeps the docstring's promise is to charge the **difference of the
rounded totals**: the fraction stays in `amount`, the cent is charged on the turn the total crosses
it, and the meter is never more than half a cent behind the truth. `None` then means what it says,
and `cents` asks `cost_seen` rather than `amount == 0`, because a provider that priced a turn at
nothing has told us something and filing that under unknown throws it away.

---

### [NOTE] 2026-09-10 — Group 5: BUG-012 was five promises, and one of them was BUG-005 again
Topics: agent, compose, transcript, patterns
Affects-phases: none
Affects-specs: none

Four of the six shipped patterns are built on `compose`, and `compose` produced a transcript no
provider would accept. Its results were matched to tool calls by `call.id`, which cannot work for a
plan whose step ids are the model's own; and because `compose` is a meta-tool, the loop skipped it
and left the call **unanswered**. That is the dangling tool call Anthropic, OpenAI and Google all
reject — the same rule BUG-005 was about, in a second place, found by reading rather than by
running, because every test used a scripted model that does not enforce the pairing rule.

The audit's row said the step results were dropped. Measured, it was worse: one call made, zero
results returned, and a request that would have 400'd.

The other four were promises with no caller. `Pattern.ceiling` appeared **zero** times in
`component.py`; so did `missing_for`. A field that is parsed, held and read by nothing is worse than
a field that does not exist, because a team writing `[ceiling]` into a pattern file reads it as a
guarantee. `skills.py` even said when its check runs — *before the first turn* — and there was no
first turn for it to run before, because `AgentComponent` had nowhere to put a skill.

**An existing test caught a regression I introduced.** Wrapping the provider call, I put
`await self.catalogue()` inside the catch, so BUG-001's own refusal — a registered tool named like a
meta-tool — came back as `provider_failed`. Three Phase 13 tests failed immediately. The catch is
for the provider, not for our own refusals, and the request is built outside it now.

---

### [NOTE] 2026-09-10 — Group 5: the debts that only reach someone who installed a wheel
Topics: packaging, invariants, types
Affects-phases: none
Affects-specs: none

Every part of TD-003 is invisible from inside the workspace. `uv` resolves the whole thing here, so
an undeclared dependency imports fine, an unpinned one gets the right version, and a missing
`py.typed` types perfectly — right up until somebody installs one wheel.

So the tests read the **shipped metadata** rather than the source, and the marker was verified by
opening a built wheel: `shadow_hdk_adapters_mqtt-0.12.0-py3-none-any.whl` carries
`shadow_hdk/adapters/mqtt/py.typed` and requires `shadow-hdk-kernel==0.12.0`. Reading the
artifact rather than the tree is the same move J2's licence check made, for the same reason.

The wire importing `adapters.basic` is *no adapter imports another* one layer up, and it took the
remedy that rule already names — `SystemClock` moved below both — rather than a new dependency.
Nothing about reading the wall clock is adapter-shaped, which is what made the move uncontroversial.

**The invariant file asserts its own coverage.** BUG-007 was a package the gate skipped, and the
package with the undeclared dependency was the one nothing walked. So the new file checks that the
set it walks is every package on disk, not every package somebody remembered to add.

One mutation survived: the pin check compared whole strings, so `>=0.12.0` passed — a floor, which
is precisely what the rule forbids. It parses the distribution name now.

---

### [NOTE] 2026-09-10 — Phase 18 is done, and CI has still never run
Topics: ci, honesty, td-009
Affects-phases: none
Affects-specs: none

Every P0 and every P1 the audit filed is closed. Eighteen phases, 141 commits, 837 tests, mypy
strict over 132 files — and **not one of those commits has ever been checked by anything but this
laptop**, because the workflow triggered only on pushes to `main` and `staging` and on pull
requests, and nothing has ever reached either.

That is worth stating plainly next to every "four zeros" this lane has written. They were run, and
they were run in one place, on one machine, on one operating system. The trigger is widened now, so
the next push is the first real check.

The pull request that would land the stack is **prepared and not opened**, in `specs/adhoc/TD-009/`,
with the exact command. Opening one is an outward-facing act on the owner's repository: it names
them as author, it can notify a team, and where rules are attached it can start a merge. That is
the owner's, and the rule has been the same since Phase 0.

The record also says what to expect from a red, because a first run is information rather than a
regression: the 90% coverage floor has never been measured off this machine; the one test skipped
here for want of `prlimit` will actually **run** on Linux, and is the one most likely to find
something; and the ten `live` tests stay deselected because they need a broker, a server or a paid
turn.

---
