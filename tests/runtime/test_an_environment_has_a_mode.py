"""One environment, one mode, one derivation — true for every operation in it (D48).

Three adapters each held an opinion about the same boundary and one of them lied (BUG-018). The
mature runtimes answer with one concept: an environment with a mode — `read-only`,
`workspace-write`, `full` — enforced once, so every operation's effect profile is derived from the
same three facts and is true for the same reason.

**The derivation is over what is *true*, never what is *wanted*.** `Isolation` says what the
environment can actually make so — writes confined, reads confined, network denied — and it is
established by a proof or by an honest *no*, never declared by a wrapper. A mode that the
isolation cannot make true is refused at construction (`CannotEnforce`), because a host that asked
for confinement and cannot have it must know rather than find out.
"""

from __future__ import annotations

import pytest

from shadow_hdk.kernel import ScopeSet
from shadow_hdk.runtime.environment import CannotEnforce, Isolation, effects_of, requires

WORKSPACE = ScopeSet.of("workspace")
EVERYTHING = ScopeSet(everything=True)

CONFINED = Isolation(writes_confined=True, reads_confined=False, network_denied=True, proven=True)
OPEN = Isolation(writes_confined=False, reads_confined=False, network_denied=False, proven=False)
FULLY = Isolation(writes_confined=True, reads_confined=True, network_denied=True, proven=True)


# ------------------------------------------------------------------ the derivation


def test_a_read_in_a_confined_environment_still_reads_everything_unless_reads_are_confined() -> (
    None
):
    """Seatbelt confines writes and leaves reads open — the interpreter has to read its own
    installation — so `reads` is honest about that even in `workspace-write`."""
    assert effects_of(CONFINED, "workspace-write", "read").reads == EVERYTHING
    assert effects_of(FULLY, "workspace-write", "read").reads == WORKSPACE


def test_a_write_in_workspace_write_is_confined_when_the_isolation_confines_it() -> None:
    assert effects_of(CONFINED, "workspace-write", "write").writes == WORKSPACE
    assert effects_of(OPEN, "full", "write").writes == EVERYTHING


def test_running_code_is_every_field_of_the_environment_at_once() -> None:
    """A command can read, write and reach whatever the environment lets it; its profile is the
    union of the environment's truths, not a guess about what the command will do."""
    run = effects_of(CONFINED, "workspace-write", "run")

    assert run.reads == EVERYTHING
    assert run.writes == WORKSPACE
    assert run.reaches is False
    assert run.reversible is False
    assert run.contained is True

    loose = effects_of(OPEN, "full", "run")
    assert loose.writes == EVERYTHING and loose.reaches is True and loose.contained is False


def test_read_only_declares_no_writes_at_all() -> None:
    """Not `{workspace}` — *nothing*. A mode that writes nothing has no write scope, and a policy
    that permits no writes admits it."""
    assert effects_of(CONFINED, "read-only", "read").writes == ScopeSet()
    assert effects_of(CONFINED, "read-only", "run").writes == ScopeSet()


def test_contained_is_the_proof_and_nothing_else() -> None:
    """`contained` is not a mode. An environment in `full` mode inside a proven box is still
    contained; one in `workspace-write` on a host with no sandbox is not, whatever it wanted."""
    assert effects_of(FULLY, "full", "run").contained is True
    assert effects_of(OPEN, "workspace-write", "run").contained is False


# ------------------------------------------------------------------ enforced or refused


def test_a_mode_the_isolation_cannot_make_true_is_refused_naming_the_gap() -> None:
    with pytest.raises(CannotEnforce, match="writes"):
        requires(OPEN, "workspace-write")
    with pytest.raises(CannotEnforce, match="writes"):
        requires(OPEN, "read-only")


def test_full_is_always_enforceable() -> None:
    """`full` asks for nothing, so nothing can fail to provide it."""
    requires(OPEN, "full")
    requires(FULLY, "full")


def test_a_confined_mode_needs_the_network_denied_too() -> None:
    """Codex's `workspace-write` denies the network; a box that confines writes but leaves a
    socket open has a hole the mode does not admit."""
    leaky = Isolation(writes_confined=True, reads_confined=False, network_denied=False, proven=True)

    with pytest.raises(CannotEnforce, match="network"):
        requires(leaky, "workspace-write")


def test_an_unproven_confinement_does_not_count() -> None:
    """A wrapper that *says* it confines and was never watched denying anything is a claim (D36)."""
    claimed = Isolation(
        writes_confined=True, reads_confined=False, network_denied=True, proven=False
    )

    with pytest.raises(CannotEnforce, match="proven"):
        requires(claimed, "workspace-write")
