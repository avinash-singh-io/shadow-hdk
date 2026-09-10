---
type: History
phase: 3-workspace-and-code
---

# Phase 3 — history

Append-only. Newest at the bottom.

| Entry type | Meaning |
|---|---|
| `[DECISION]` | a choice made, with what it rules out |
| `[ARCH_CHANGE]` | a structural change to the code or the specs |
| `[DISCOVERY]` | something the code or a library turned out to be |
| `[CORRECTION]` | a previous entry or plan proven wrong |

---

### [ARCH_CHANGE] 2026-09-10 — branched from Phase 2
Topics: branches, chain

`phase-3-workspace-and-code` is cut from `phase-2-the-spike` at `05000c2`. The chain is Phase 0 →
1 → 2 → 3; nothing merges until the owner lands it.

### [DECISION] 2026-09-10 — `contained` is a deployment fact with no default
Topics: sandbox, contained, effects, governance

`09` §5's third form of "program" is *code in a sandbox — present only on deployments that have
one, absent everywhere else*. The temptation is to make that a policy question answered per call.
It is not: it is a fact about the machine, stated once.

`SubprocessSandbox(root, *, contained, …)` therefore takes `contained` keyword-only **with no
default**, and carries it verbatim into the effect profile. A deployment with no real isolation
constructs it `contained=False`, a mode whose ceiling requires containment then refuses every
invocation, and the component is **absent from the catalogue** rather than refused at call time — so
the model never sees a tool it may not use.

Why no default: a sandbox that claimed containment it did not have would be the most dangerous lie
in this system. There is no safe value to guess, so it is not guessed.

**And the honest label:** a subprocess with a timeout is a *leash*, not a boundary. It stops a
runaway; it does not stop a determined program. That is why the default posture on a laptop is
`contained=False` and why Phase 11 exists.

### [ARCH_CHANGE] 2026-09-10 — Group 0: a workspace with one way in and no way out
Topics: workspace, confinement, symlinks, effects, g0

`WorkspaceComponents(root)` — `read_file`, `write_file`, `list_dir`, `delete_file`. 17 tests, seven
mutations, all biting.

**The confinement is one function and it resolves before it checks.** `Path.resolve()` follows
symlinks and normalises `..`, so what is compared is the *real* destination rather than the
spelling. Comparing the spelling is the bug this exists to avoid, and there is a test with a **real
symlink on a real disk** to prove it: `innocent.txt` inside the root, pointing at a file outside it,
refused. A mutation that drops the `.resolve()` fails the suite.

Three escapes, each refused **as an observation** rather than raised: `..`, an absolute path, and
the symlink. An agent gets a `Failed` it can route around; a traceback would end its run for what is
a perfectly ordinary mistake.

**Deleting is a different permission from writing.** `write_file` declares `reversible: true` and
`delete_file` declares `reversible: false`, so a mode may let an agent change things without letting
it destroy them — one profile field carrying a distinction a product would otherwise need a rule
for.

**`writable=False` removes the writing components** rather than refusing them at call time. Absent,
not greyed out, which is the rule everywhere else in this design.

### [DISCOVERY] 2026-09-10 — the benchmark flaked, and a flaky gate is worse than none
Topics: benchmark, d11, tooling

The full-suite gate failed on `test_a_hundred_sequential_steps`: **308.1 ms** against a 300 ms
ceiling. Measured immediately afterwards in isolation, the same code ran **52.7, 56.2 and 60.7 ms**,
and 53.7 ms inside the suite. It was contention — the run was spawning MCP subprocesses at the time
— not a regression.

The fix is not more slack, which would have blunted the signal. It is **best of three**: a busy
machine makes a run slower and never faster, so the minimum is the cleanest estimate of what the
code costs. Averaging would have buried the real number under the contention; a single run reported
the contention as if it were the number.

Now: **54.3 ms (0.543 ms/step, best of 3)** and a 50-way fan-out in **15.4 ms**, against D11's
100 ms / 1 ms / 50 ms. The budget stays where it was.
