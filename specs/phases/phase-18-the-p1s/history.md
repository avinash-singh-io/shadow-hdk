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
