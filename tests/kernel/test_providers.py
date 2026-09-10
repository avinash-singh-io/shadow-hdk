"""What a provider is, before anything knows how to run one (D40, D41).

A provider is **data**: a binary, some probes, some environment rules, a transport. The record is a
kernel type for the same reason `EffectProfile` is — it is a fact with no I/O in it, and the thing
that acts on it lives above.

Two rules are load-bearing here and both are about **not guessing**:

**Every default is the conservative one.** A record that omitted a field must never read as a
permission. `EffectProfile` established this — `ASSUME_WORST` where an annotation says nothing — and
a provider follows it: no auth probe means the answer is `unknown`, never `ready`.

**`unknown` is an answer.** The reference implementation carries three auth states, and the third is
the one that matters: some CLIs cannot be asked. A runtime reporting *not signed in* because it
could not tell sends somebody to fix what is not broken.
"""

from __future__ import annotations

import pytest

from shadow_hdk.kernel import Provider, ProviderKind, ProviderStatus
from shadow_hdk.kernel.contracts import round_trip

CLAUDE = Provider(
    id="claude-code",
    kind="agent",
    bin="claude",
    fallback_bins=("openclaude",),
    version_probe=("--version",),
    auth_probe=("auth", "status"),
    strip_env=("CLAUDECODE",),
)


# ------------------------------------------------------------------ the record


def test_a_provider_says_what_it_is_and_how_to_find_it() -> None:
    assert CLAUDE.id == "claude-code"
    assert CLAUDE.kind == "agent"
    assert CLAUDE.bin == "claude"
    assert CLAUDE.fallback_bins == ("openclaude",)


def test_a_provider_is_frozen() -> None:
    """It is read from a file and handed around; nothing downstream may edit it in place."""
    with pytest.raises(Exception):  # noqa: B017 — dataclasses raise FrozenInstanceError
        CLAUDE.bin = "something-else"  # type: ignore[misc]


def test_the_two_kinds_are_the_two_seams() -> None:
    """D39. A provider sells inference or it sells agency, and nothing else is a provider."""
    assert set(ProviderKind.__args__) == {"model", "agent"}  # type: ignore[attr-defined]


def test_a_bare_provider_claims_nothing() -> None:
    """The conservative default, the way `EffectProfile` does it: a record that says nothing must
    not read as a permission to do anything."""
    bare = Provider(id="x", kind="model", bin="x")

    assert bare.fallback_bins == ()
    assert bare.version_probe == ()
    assert bare.auth_probe == ()
    assert bare.strip_env == ()
    assert bare.set_env == ()
    assert bare.minimum_version is None
    assert bare.injects_tools is None, "a provider that did not say it takes our tools, has not"


# ------------------------------------------------------------------ the answer


def test_status_has_five_answers_and_one_of_them_is_that_we_could_not_tell() -> None:
    assert set(ProviderStatus.__args__) == {  # type: ignore[attr-defined]
        "ready",
        "absent",
        "not-signed-in",
        "too-old",
        "unknown",
    }


# ------------------------------------------------------------------ the contract


def test_a_provider_round_trips_through_json() -> None:
    """D19: every published type survives the wire, because a host in another language reads its
    provider library too."""
    assert round_trip(CLAUDE, Provider) == CLAUDE
