#!/usr/bin/env python3
"""Apply one anchored text mutation, run a test selection, restore the file.

`project-rules.md` requires every assertion to be mutation-checked, and the repository had no tool
for it — so every session wrote its own, and phase 64's did it wrong three times: one stalled on
`uv run` lock contention, one was **vacuous** (a shell function never passed its arguments, so
nothing was mutated and all seven reported success), and one hung. This exists so the next session
does not have to rediscover that.

    python3 scripts/mutate-one.py <file> <old> <new> <test...>

It **exits non-zero when the anchor is missing or ambiguous**, which is the whole point: a mutation
that did not apply proves nothing, and a pass you cannot distinguish from a no-op is worse than no
check at all. `BITES` means the mutation was caught; `*** SURVIVED ***` means an assertion does not
bite and is either weak or the mutant is equivalent — resolve the second by deleting the code, not
by inventing a test that cannot tell the difference.

Beware equivalent mutants and no-op mutants (`() or x` is `x`). Both report SURVIVED and neither is
a test weakness. The file is restored in a `finally`, but a killed runner leaves it mutated — check
`git status` if you interrupt one.
"""
import pathlib, subprocess, sys

src, old, new, tests = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
p = pathlib.Path(src)
original = p.read_text()
if old not in original:
    print(f"ANCHOR-MISSING in {src}: {old[:90]!r}")
    sys.exit(2)
if original.count(old) != 1:
    print(f"ANCHOR-AMBIGUOUS ({original.count(old)}x) in {src}: {old[:90]!r}")
    sys.exit(2)
p.write_text(original.replace(old, new, 1))
try:
    done = subprocess.run(
        ["uv", "run", "pytest", "-x", "-q", "-p", "no:randomly", "--timeout=60", *tests],
        capture_output=True, text=True, timeout=600,
    )
    out = (done.stdout + done.stderr).strip().split("\n")[-1]
    verdict = "BITES" if done.returncode != 0 else "*** SURVIVED ***"
    print(f"{verdict}  {new[:70]!r}  -> {out}")
except subprocess.TimeoutExpired:
    print(f"TIMEOUT  {new[:70]!r}")
finally:
    p.write_text(original)
