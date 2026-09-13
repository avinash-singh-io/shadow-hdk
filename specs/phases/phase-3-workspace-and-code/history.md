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

`phase-3-workspace-and-code` is cut from `phase-2-the-spike` at `beb9efa`. The chain is Phase 0 →
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

### [DISCOVERY] 2026-09-10 — an uncontained host cannot promise it will not reach the network
Topics: sandbox, effects, reaches, honesty, g1

The plan said the sandbox declares `reaches = network`. Building it made the flaw obvious: a plain
subprocess on an ordinary host can open a socket whatever we pass it. `network=False` on an
uncontained machine is not a restriction, it is a *wish*, and a profile that stated it would be
feeding the governance system a claim nothing enforces.

`reaches` is therefore **`network or not contained`**. Only a deployment asserting real isolation
gets to say a run does not reach outside; everywhere else the answer is yes, because that is true.
A mutation that reverts it to plain `network` fails the suite.

This is the same shape as the MCP rule from Phase 1 — *an effect nobody vouched for is assumed to be
the worst one* — arriving from the other direction: there, a server said nothing; here, we cannot
keep the promise ourselves.

### [ARCH_CHANGE] 2026-09-10 — Group 1: a leash, and an honest label
Topics: sandbox, timeout, output, env, g1

`SubprocessSandbox(root, *, contained, timeout_s=30, output_limit=64_000, network=False)` with
`run_python` and `run_shell`. 18 tests, eight mutations, all biting.

**A non-zero exit is `Completed`, not `Failed`.** The script ran perfectly well and told us it
failed; that is a result the agent can read, not an error for the runtime to dress up. `Failed` is
reserved for *the script did not run* — a timeout, a broken exec.

**The timeout is measured rather than asserted.** A test that only checked for `Failed` would pass
even if the timeout never fired and something else went wrong, so it times the call: a script
sleeping sixty seconds under a one-second limit returns in under ten.

**Truncation is said, not silent.** An agent reasoning from half an answer while believing it whole
is a worse failure than one told it only got half.

### [DISCOVERY] 2026-09-10 — a mutation found that nothing guarded the operator's secrets
Topics: sandbox, environment, credentials, mutation-check

Replacing the environment filter with `dict(os.environ)` **left the suite green**. The filter was
written deliberately — a named few variables pass, everything else is dropped — and nothing tested
it.

That is the most serious gap a mutation check has found here. A script an agent wrote is untrusted
code, and the environment is where credentials live: handing it `ANTHROPIC_API_KEY` because it
happened to be in the parent process is how a tool that reads a file also exfiltrates a token. Two
tests now — one that a planted secret comes back `ABSENT`, and one that `PATH` still arrives, because
a filter that dropped everything would pass the first and break every script.

### [ARCH_CHANGE] 2026-09-10 — Group 2: what the deployment is decides what the model can see
Topics: contained, visibility, governance, artifacts, g2

The chain, proven through a **real run** rather than by reading a profile:

```
SubprocessSandbox(contained=False)      a deployment with no real isolation, saying so
    → a mode whose ceiling requires containment
    → narrows() is False → governance refuses
    → RunContext.visible() does not list it → the model is never offered it
```

Six tests. Both halves — the same sandbox with `contained=True` is allowed *and* visible, because a
check that refuses everything is not a check. And with **allow-all instead of a mode, nothing is
hidden**: the uncontained sandbox is offered, which says plainly that hiding it is governance's
doing and not the adapter's.

`write_file` stays visible throughout: the careful mode permits writing and forbids only running
code. That is the distinction being made — *make things* and *run things* are different
permissions — and it is one field of one profile.

**And what all of it is for**: an agent writes `notes.md` and `out/page.html` through the workspace
components on a real run, and the files are on disk when it is done.

A mutation that stops `visible()` filtering through governance fails the suite, so the last link in
the chain is not decorative.

### [ARCH_CHANGE] 2026-09-10 — Phase 3 complete; Phase 4 branches from here
Topics: phase, chain, exit

Three groups. **251 tests**, ruff and mypy strict clean over 56 files, benchmark 54.3 ms
(0.543 ms/step, best of 3). Nothing merged. Every acceptance criterion in `overview.md` is met.

Phase 4 — the ACP bridge — branches from this one, and starts knowing two things Phase 2 measured:
it inherits a fourteen-method client surface, and it needs its own wall clock because nothing in ACP
stops an agent looping on a denial.
