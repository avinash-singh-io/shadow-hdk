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
