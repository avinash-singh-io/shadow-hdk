"""What a document says is here, is here (TD-008).

The audit's complaint was that the constitutional documents each describe a different day, and it
listed the drift item by item. Fixing the items fixes a day; this file fixes the class.

Two rules, both cheap and both mechanical:

**A path a document names must exist.** `CLAUDE.md` sent a reader to `docs/developer-guide.md` and
to `tests/benchmarks/`, neither of which was ever written; `file-structure.md` listed four adapter
directories that do not exist. A dead path is worse than no path — it reads as a promise that
somebody else already did the work.

**The adapter list matches the tree.** `file-structure.md` named `effect_rules/`, `sandbox_gvisor/`
and `sandbox_firecracker/`, which are `modes/` and `contained/`, and a `patterns/` directory of
markdown that turned out to be TOML files inside the agent adapter. A reader following that map
looks for four things that are not there and misses two that are.

**Placeholders are not paths.** A document is allowed to write `specs/phases/<phase>/tasks.md` or
`specs/changelog/YYYY-MM.md`, and a rule that could not tell those from rot would be turned off
within a week. Anything holding `<`, `*`, `YYYY` or `NNNN` is a shape, not a location.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"

ROOTS = ("packages/", "specs/", "tests/", "docs/", "examples/", "spikes/", ".github/", ".githooks")
"""The prefixes that make a backticked string a claim about this repository."""

PLACEHOLDER = ("<", "*", "YYYY", "NNNN")
BACKTICKED = re.compile(r"`([^`\s]+)`")


def documents() -> list[Path]:
    """Every spec document, `CLAUDE.md` and `README.md` — but not the changelog.

    A changelog is a record of what happened, and one of its entries names a file another agent
    later deleted. Rewriting history to keep a path alive would be worse than a dead link in a line
    that was true when it was written.

    **The README is in this net for the same reason the specs are, and more urgently.** It is the
    first file anybody opens and the last one anybody re-reads, so it rots faster than anything it
    describes — the version this rule inherited still announced Phase 0, 150 tests and version
    0.1.0, and called the project unlicensed a day after it was released under MIT. Nothing here
    can check a stale *number*; naming a path that is not there is the part a rule can catch.
    """
    return [
        *(d for d in sorted(SPECS.rglob("*.md")) if "changelog" not in d.parts),
        ROOT / "CLAUDE.md",
        ROOT / "README.md",
    ]


def dead_paths(docs: list[Path], root: Path) -> list[str]:
    """Every repo path a document names that is not there."""
    dead: list[str] = []
    for document in docs:
        if not document.exists():
            continue
        for found in BACKTICKED.findall(document.read_text(encoding="utf-8")):
            candidate = found.split(":")[0].rstrip(",.;")
            if not candidate.startswith(ROOTS) or any(p in candidate for p in PLACEHOLDER):
                continue
            if not (root / candidate).exists():
                dead.append(f"{document.relative_to(root)}: {candidate}")
    return sorted(set(dead))


def adapters_named(document: Path) -> set[str]:
    """The adapter directories the tree claims, read from the `adapters/` block alone.

    Bounded to the block: the first version read to the end of the file and collected `kernel/`,
    `runtime/` and the test directories as adapters, which fails for a reason it is not about.
    """
    lines = document.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "adapters/")
    depth = len(lines[start]) - len(lines[start].lstrip())
    child: int | None = None
    named: set[str] = set()
    for line in lines[start + 1 :]:
        if not line.strip():
            continue
        here = len(line) - len(line.lstrip())
        if here <= depth:
            break
        if child is None:
            child = here
        # Only the block's own children. An adapter's subdirectory — `agent/library/`, where the
        # shipped patterns live — is not an adapter, and counting it made this fail for a reason
        # it is not about.
        if here == child and (found := re.match(r"\s+(\w+)/", line)):
            named.add(found.group(1))
    return named


def test_no_document_names_a_path_that_is_not_there() -> None:
    dead = dead_paths(documents(), ROOT)

    assert not dead, "\n  ".join(["documents naming paths that do not exist:", *dead])


def test_the_adapter_list_matches_the_tree() -> None:
    """The one listing a reader navigates by, held to the directory it describes."""
    on_disk = {p.name for p in (ROOT / "packages" / "adapters").iterdir() if p.is_dir()}
    named = adapters_named(SPECS / "architecture" / "file-structure.md")

    assert named - on_disk == set(), f"named but not on disk: {sorted(named - on_disk)}"
    assert on_disk - named == set(), f"on disk but not named: {sorted(on_disk - named)}"


def modules_named(document: Path) -> set[str]:
    """The runtime modules a document's table claims, as `` `name.py` `` in a first column."""
    return set(re.findall(r"^\| `(\w+\.py)`", document.read_text(encoding="utf-8"), re.MULTILINE))


def test_the_runtime_module_table_matches_the_tree() -> None:
    """`runtime.md` names the modules a reader is meant to navigate by, and it named thirteen of
    twenty. The seven it missed are the ones that arrived after it was written — cancellation,
    children, the clock, devices, the leash, process groups and replay — which is precisely the set
    a reader would not know to look for."""
    on_disk = {p.name for p in (ROOT / "packages/runtime/src/shadow_hdk/runtime").glob("*.py")}
    named = modules_named(SPECS / "architecture" / "runtime.md")

    assert named - on_disk == set(), f"named but not on disk: {sorted(named - on_disk)}"
    assert on_disk - named == set(), f"on disk but not named: {sorted(on_disk - named)}"


# --------------------------------------------------------------------------- the anti-vacuity pair


def test_the_rules_catch_what_they_look_for(tmp_path: Path) -> None:
    """Both rules against cases that break them, because the real tree satisfies both once fixed
    and a deleted predicate would otherwise leave the suite green — the hole a mutation pass found
    in two other invariants this phase."""
    (tmp_path / "specs").mkdir()
    rotten = tmp_path / "specs" / "doc.md"
    rotten.write_text(
        "See `packages/gone/` and `specs/phases/<phase>/tasks.md` and `tests/`.\n", encoding="utf-8"
    )
    (tmp_path / "tests").mkdir()

    dead = dead_paths([rotten], tmp_path)

    assert dead == ["specs/doc.md: packages/gone/"], dead


def test_the_listing_rules_catch_what_they_look_for(tmp_path: Path) -> None:
    """The two list comparisons, against trees that disagree with their documents.

    Found by a mutation pass: deleting either *on disk but not named* assertion left the suite
    green, because the real listings match once fixed — the fourth time this phase that a rule
    could not be **seen** to work. `dead_paths` already had this pair; the parsers did not.
    """
    tree = tmp_path / "file-structure.md"
    tree.write_text(
        "  packages/\n    adapters/\n      basic/    a\n      mqtt/     b\n"
        "        library/  not an adapter\n  tests/\n    invariants/  x\n",
        encoding="utf-8",
    )

    assert adapters_named(tree) == {"basic", "mqtt"}, adapters_named(tree)

    table = tmp_path / "runtime.md"
    table.write_text(
        # Prose mentioning a module is not the table naming one — a parser that matched any
        # backticked `.py` would collect `emit.py` here and report the table as complete when it
        # is not. A mutation loosening the anchor survived until this line existed.
        "The drive lives in `loop.py` and talks to `emit.py`.\n\n"
        "| `step.py` | one governed step |\n| `loop.py` | the drive |\n| `testing/` | doubles |\n",
        encoding="utf-8",
    )

    assert modules_named(table) == {"step.py", "loop.py"}


def test_the_walk_reads_the_documents() -> None:
    """A scan over nothing would make the first rule vacuous."""
    assert len(documents()) >= 20
    assert any(d.name == "file-structure.md" for d in documents())
    assert any(d.name == "README.md" for d in documents()), "the front door is outside the net"
