"""An uncontained sandbox reaches the whole machine, and must say so (BUG-018).

Found by running the coder example: asked for a landing page, the agent called `run_shell`, and the
output carried `specs/status.md`, a listing of the repository's **parent** directory, and files from
unrelated projects on the disk. Nothing refused it, because nothing had been told there was
anything to refuse.

`effects` declared `reads: {workspace}` and `writes: {workspace}` **whatever `contained` said**. A
plain subprocess honours `cwd` and nothing else: `cd ..` works, an absolute path works, and the
whole filesystem is one command away. So the profile a policy judged was false in its two most
important fields, and a mode permitting workspace writes was in fact permitting writes anywhere.

The same function got this right for `reaches` and its docstring said why — *a governance system
fed a lie is worse than one fed nothing*. The rule was written down and applied to one field of
three.

**What containment changes is what is true, not what is claimed.** A sandbox that proves it is
contained (D25, D36) may narrow these; one that cannot, may not.
"""

from __future__ import annotations

from pathlib import Path

from shadow_hdk.adapters.sandbox_subprocess import SubprocessSandbox

from shadow_hdk.kernel import ScopeSet

WORKSPACE = ScopeSet.of("workspace")
EVERYTHING = ScopeSet(everything=True)


def test_an_uncontained_sandbox_admits_it_reads_everything(tmp_path: Path) -> None:
    """The bug, stated as the claim it broke."""
    loose = SubprocessSandbox(tmp_path, contained=False)

    assert loose.effects.reads == EVERYTHING, "it claimed the workspace and can read the disk"


def test_an_uncontained_sandbox_admits_it_writes_everything(tmp_path: Path) -> None:
    """The more dangerous half: a mode permitting `writes: {workspace}` was letting a shell command
    write anywhere on the machine, and the record said the workspace."""
    loose = SubprocessSandbox(tmp_path, contained=False)

    assert loose.effects.writes == EVERYTHING


def test_a_contained_sandbox_may_narrow_to_the_workspace(tmp_path: Path) -> None:
    """Containment is what makes the narrower claim true. A deployment that proves isolation gets
    to say so — and only then."""
    proven = SubprocessSandbox(tmp_path, contained=True)

    assert proven.effects.reads == WORKSPACE
    assert proven.effects.writes == WORKSPACE
    assert proven.effects.contained is True


async def test_the_declaration_matches_what_it_actually_does(tmp_path: Path) -> None:
    """The anti-vacuity half, and the part that makes this a measurement rather than an opinion:
    run a command that reads outside the workspace and watch it succeed."""
    outside = tmp_path.parent / "not-in-the-workspace.txt"
    outside.write_text("readable from outside\n", encoding="utf-8")
    root = tmp_path / "workspace"
    root.mkdir()
    loose = SubprocessSandbox(root, contained=False)

    try:
        done = await loose.invoke("run_shell", {"command": f"cat {outside}"})
    finally:
        outside.unlink()

    assert "readable from outside" in str(done), (
        "the arrangement failed: it could not reach outside after all, and the claim "
        "this test is about would have been true"
    )


async def test_it_can_write_outside_the_workspace_too(tmp_path: Path) -> None:
    """The half that matters most, proven rather than argued."""
    root = tmp_path / "workspace"
    root.mkdir()
    target = tmp_path.parent / "written-from-inside-the-sandbox.txt"
    loose = SubprocessSandbox(root, contained=False)

    try:
        await loose.invoke("run_python", {"source": f"open({str(target)!r}, 'w').write('out')"})
        wrote_outside = target.exists()
    finally:
        target.unlink(missing_ok=True)

    assert wrote_outside, "the arrangement failed: it could not write outside after all"
