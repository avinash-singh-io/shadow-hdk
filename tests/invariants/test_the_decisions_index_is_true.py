"""Every decision is findable, and the map says where (TD-008).

The decisions live beside the work that forced them — D36 next to the fake `runsc`, D38 next to the
transcript of a policy overruling a human — and that is deliberate: copying them into one folder
would make a second version of each to keep in step, which is the disease this row describes rather
than a cure for it.

What was wrong is that nothing pointed at them. `specs/decisions/` held a template, and
`CLAUDE.md`'s *why was X chosen* sent a reader there.

A map fixes that once and rots immediately, so this is the pair that keeps it true: every decision
in the tree appears in the index, and every row of the index points at a document that really
contains it. A decision taken and not listed fails the first; a renamed file fails the second.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
INDEX = SPECS / "decisions" / "index.md"

HEADING = re.compile(r"^## D(\d+) —|^### \[DECISION\][^\n]*\bD(\d+):", re.MULTILINE)
ROW = re.compile(r"^\| D(\d+) \| [^|]+ \| \[`([^`]+)`\]", re.MULTILINE)


def declared() -> dict[int, Path]:
    """Every `D<n>` heading under `specs/`, and the document it is in."""
    found: dict[int, Path] = {}
    for document in sorted(SPECS.rglob("*.md")):
        if document == INDEX:
            continue
        for first, second in HEADING.findall(document.read_text(encoding="utf-8")):
            found.setdefault(int(first or second), document)
    return found


def listed() -> dict[int, str]:
    return {int(n): where for n, where in ROW.findall(INDEX.read_text(encoding="utf-8"))}


def test_every_decision_is_in_the_index() -> None:
    missing = sorted(set(declared()) - set(listed()))

    assert not missing, f"decisions taken and not listed: {[f'D{n}' for n in missing]}"


def test_the_index_lists_nothing_that_is_not_a_decision() -> None:
    """The other direction, which rots silently: a row left behind by a renumbering."""
    stray = sorted(set(listed()) - set(declared()))

    assert not stray, f"listed but nowhere in the tree: {[f'D{n}' for n in stray]}"


def test_every_row_points_at_a_document_that_contains_it() -> None:
    """A path in a table is a promise. This is what makes it one — the file must exist *and* the
    decision must be in it, so a move that updates neither is caught."""
    wrong: list[str] = []
    for number, where in sorted(listed().items()):
        document = SPECS / where
        if not document.exists():
            wrong.append(f"D{number}: {where} does not exist")
            continue
        text = document.read_text(encoding="utf-8")
        if not any(int(a or b) == number for a, b in HEADING.findall(text)):
            wrong.append(f"D{number}: {where} does not contain it")

    assert not wrong, "\n  ".join(["the index points somewhere wrong:", *wrong])


def test_the_walk_finds_the_decisions() -> None:
    """A scan that found nothing would make all three guards vacuous — BUG-007's shape, and the
    reason `test_stands_alone.py` carries the same pair."""
    assert len(declared()) >= 38, f"the walk found only {sorted(declared())}"
