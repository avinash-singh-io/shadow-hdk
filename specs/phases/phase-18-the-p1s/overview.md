---
type: Phase
phase: 18
name: the-p1s
epic: 0008-what-the-audit-found
status: not-started
topics: [audit, workspace, leash, containment, resume, d35, d36]
deps: [phase-17-the-audit]
---

# Phase 18 — The audit's P1s

Phase 17 closed the audit's four P0s. These are the six P1s and two tech-debt rows, and the same
rule holds: **every row is reproduced before it is fixed.**

## What was measured before anything was written

Against a temporary directory and files the probe created — never anything real:

```
1. read through a hard link -> Completed(output='THE-OUTSIDE-CONTENT')
   write through it         -> Completed(...)  | the outside file now: OVERWRITTEN
2. a NUL byte RAISED out of invoke -> ValueError: embedded null character in path
3. leashed run -> Completed(exit_code=0, stdout='started')
   marker written AFTER the step returned: True -> alive
4. HOME in the child -> HOME=/Users/<the operator>
5. a five-line fake runsc on PATH -> "gvisor proved containment: Starting gVisor..."
```

All five as filed. The fifth is the one that matters most, and it is the shape BUG-007 had: a
check that looks like a gate and is not.

## Group 1 — the workspace and the leash (BUG-008, BUG-009 except the proof)

`_resolve` follows symlinks and normalises `..`, which is the bug it was written to avoid — but a
**hard link is not a link**: it is the outside inode, with its own name inside the root, and
`Path.resolve()` has nothing to resolve. So confinement is checked by the *name* after all. The
fix is to ask the filesystem what the file is: refuse a regular file with more than one link, and
compare `st_dev`/`st_ino` against what the root contains. A `ValueError` from a NUL byte is caught
where every other filesystem refusal already is — a component that raises is a contract breach
(D7), whatever the reason.

### D35 — a step owns the process tree it starts

`run_leashed` killed the direct child on timeout and nothing else, so a backgrounded process
outlived the step that created it — an effect with no step to attribute it to, running after its
lease ended. A leashed program now gets **its own process group**, and the group is killed when
the leash returns, timeout or not.

**Rejected.** *Kill only on timeout* — that is what let the marker be written; a program that exits
cleanly can leave more behind than one that hangs. *Leave detached children alone as a feature* —
the harness's claim is that every effect is attributed to a step, and a process that outlives its
step is the counter-example.

`HOME` leaves `KEPT_ENV`: a script that declared `writes: {workspace}` could read `~/.ssh` or empty
the home directory. `TMPDIR` stays, pointed at the workspace. Memory and CPU limits go on where the
platform has them, and `adapters.md`'s `memory_mb` becomes true rather than aspirational. Output is
capped as it arrives rather than after `communicate()` has buffered all of it, so the cap bounds
memory and not just the observation.

## Group 2 — a proof is a capability test (BUG-009's last part)

### D36 — containment is proven by attempting what must be denied, never by a banner

`GVisor.probe()` ran `dmesg` inside the sandbox and matched the string `gVisor` in the output —
that is, it asked *the thing being trusted* to say it was trustworthy, and believed it. A five-line
shell script passed. Worse than no check: `ContainedSandbox` refuses to exist without a `Proof`, so
a deployment that got one believes containment was established.

A proof is now a **capability test**: the sandbox is asked to do something a contained program must
not be able to do, and the proof is that it failed. What the backend *says* is kept as a separate,
plainly-named `declared` field — the backend's own word, never evidence. A backend that cannot be
capability-tested does not silently pass: the deployment must say, in a named argument, that it is
trusting a claim.

## Groups 3–5

BUG-015 (a held child does not survive its parent's park — already reproduced), then BUG-010
(`Await`/resume invokes the component twice and a re-run judgement can override a human's answer),
BUG-011, BUG-012, TD-003. **TD-009 last, and it is the owner's**: CI has never run on a phase
commit, and the fix is a workflow change plus one pull request from the top of the stack — opening
it is outward-facing, so it is prepared here and handed over.

## Done when

- every reproduction above ends the other way, each asserted by a test that would fail without the
  fix, and the five that were measured are measured again
- a fake backend that does not contain **cannot** produce a proof
- gate: ruff 0, format 0, mypy 0 over every package, pytest 0; every mutation bites or is named
