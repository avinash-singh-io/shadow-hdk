"""A child's own file tool reaches the whole machine, and the judgement must say so (BUG-018, 3/3).

Two different paths carry a file operation across this bridge, and they are **not the same
operation**:

* **Our doors** — `fs/read_text_file`, `fs/write_text_file`. We do the work, and `_inside()`
  refuses a path outside the workspace. The narrow profile is *true* because we enforce it.
* **The child's own tools** — a `read`, `edit` or `delete` the child performs itself, asking us
  only for permission first. We enforce nothing; the child's process touches the disk directly
  and honours nothing but its working directory. A narrow profile here is a claim about somebody
  else's behaviour, and it is false.

`request_permission` judged the second path on the first path's profiles. So a mode permitting
workspace edits was in fact permitting the child to edit anywhere, and the record said the
workspace — the third instance of one bug in three packages that cannot import each other, which
is why the fix for the *class* is an invariant and not this file.

Containment is what makes the narrow claim true. Without it the honest answer is *everything*.
"""

from __future__ import annotations

from shadow_hdk.adapters.acp.kinds import effects_for, reading_a_file, writing_a_file
from shadow_hdk.kernel import ScopeSet

WORKSPACE = ScopeSet.of("workspace")
EVERYTHING = ScopeSet(everything=True)

FILE_KINDS = ("read", "search", "edit", "move", "delete", "fetch")


def test_an_uncontained_childs_own_file_tools_admit_they_reach_everything() -> None:
    """The bug, for every kind that touches a file."""
    for kind in FILE_KINDS:
        judged = effects_for(kind, contained=False)

        assert judged.reads == EVERYTHING, f"{kind}: claimed the workspace, reaches the disk"
        if judged.writes != ScopeSet():
            assert judged.writes == EVERYTHING, (
                f"{kind}: claimed workspace writes, can write anywhere"
            )


def test_a_contained_childs_own_file_tools_may_narrow_to_the_workspace() -> None:
    """Containment makes the narrow claim true — and only containment."""
    for kind in ("read", "edit", "delete"):
        judged = effects_for(kind, contained=True)

        assert judged.reads == WORKSPACE, kind
        assert judged.contained is True


def test_our_own_doors_stay_narrow_because_we_enforce_them() -> None:
    """The other path, deliberately unchanged: `_inside()` refuses a path outside the root, so
    `{workspace}` is what actually happens and the profile may say so. Widening these too would
    be honest about nothing and would make a reading mode refuse a read we confine ourselves."""
    assert reading_a_file().reads == WORKSPACE
    assert writing_a_file().writes == WORKSPACE


def test_a_reading_mode_now_refuses_an_uncontained_childs_own_read() -> None:
    """What the fix changes for a policy, stated as a policy would see it: a mode that permits
    reading the workspace does not permit a tool that reads the machine."""
    from shadow_hdk.adapters.modes import Mode

    reading_the_workspace = Mode("reading", ceiling=reading_a_file())

    assert not effects_for("read", contained=False).narrows(reading_the_workspace.ceiling), (
        "a child's unconfined read was judged to fit inside 'read the workspace'"
    )
    assert effects_for("read", contained=True).narrows(reading_the_workspace.ceiling)
