---
type: Ad-hoc Record
---
# TD-015 · TD-016 — time as a gate, and bytes that can be checked

> **Type**: quick-task
> **Created**: 2026-09-30
> **Branch**: fix/TD-015-TD-016-time-and-bytes
> **Backlog**: TD-015, TD-016
> **Status**: shipped — no release; nothing in either distribution changed

Two defects in the *apparatus* rather than the product, both found by the apparatus misbehaving
while other work was being verified. Neither ships code: TD-015 is tests and configuration, TD-016
is the build.

## Current Behavior

**TD-015.** Five distinct tests failed in one afternoon on code that could not have caused any of
them — two on a laptop at load average 26, two on CI runners — each green on a re-run of the same
commit. Two causes:

- **Time standing in for a happens-before.** `await asyncio.sleep(0.05)` meant "the record's save
  has landed by now". A loaded bubblewrap runner beat it and the resumed turn read `cancelled`
  rather than `parked`, because the question was not on the record yet.
- **A wall-clock gate in the ordinary suite.** The latency budget (D11) asserts on elapsed time, so
  a busy machine fails it while the code is fine. Its own `ROUNDS` note already records this
  happening twice before.

The cost was never the red run. It was the half hour spent proving a change innocent — twice — and
the fact that a red run had stopped carrying information.

**TD-016.** Re-publishing an already-released 0.35.0 reported `Local file and index file do not
match … Local: sha256=f5feb9d1…, Remote: sha256=ce9cc713…` for the same commit in the same
container. Nothing was corrupted (PyPI is append-only per filename), but this wheel **is** the
confinement mechanism, and a binary nobody can rebuild and compare is a binary taken on trust.

## Expected Behavior

- A test waits for the **thing**, not for a number of seconds. `tests/waiting.py` polls a condition
  with a generous *failure* bound — so a slow runner waits rather than fails, and a genuine
  deadlock ends the test naming what never happened instead of hanging until the suite timeout.
- The latency budget is `benchmark`-marked and deselected from an ordinary run, **and remains a
  gate**: CI already ran it as its own step on a quiet runner, and that step now selects by marker
  rather than by an `--ignore` path repeated in three places (D77 — one rule, one implementation).
- The helper's wheel is byte-identical when the same commit is built twice, and **CI proves it**
  rather than the workflow asserting it.

## Unchanged Behavior

No shipped code. Every sleep that is *about* time — an idle timeout that must elapse, a grace
period that must expire — is untouched, because waiting for a duration is the point of those.
The benchmark's budgets, slack and best-of-nine are unchanged; only where it runs changed. The
helper's Rust source is unchanged; only how it is compiled.

## Verification Evidence

**TD-015.** CI run `36702854236`: every test job green — `macos`, `bubblewrap`, `native`, and
`check` on 3.12, 3.13 and 3.14 — on the same commit whose *local* full-suite runs had failed 7
tests and then 2 tests, in two different sets, at load average 10. That contrast is the evidence:
the suite is stable where the measurement is worth trusting, and the failures were never the code.

Locally: `uv run pytest tests/runtime/` → 504 passed, **4 deselected** (the benchmarks);
`uv run pytest -m benchmark` → 4 passed.

**TD-016.** The first attempt **failed**, and that is the result worth recording: the settings were
on the job while the compiler runs in a manylinux container, so they never reached the thing
producing the binary. Passing them through `docker-options` fixed it. CI run `36703572231`, the
`reproducible` job:

```
first  a22ffa2c16c7a043b55a111a24dd5c3612a9376ae20216b7efb8e0de29d179c2
second a22ffa2c16c7a043b55a111a24dd5c3612a9376ae20216b7efb8e0de29d179c2
```

A check that had only ever passed would have told us nothing; this one failed first, for a real
reason, and then passed.

**Note for the next release.** The determinism flags change the compiled binary, so the next
helper wheel will not match 0.36.0's bytes. That is expected — it is the last build whose bytes
nobody can reproduce.
