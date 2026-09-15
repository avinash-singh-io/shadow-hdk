"""Doubles, so a host's suite can run the harness for $0 (D8).

Every one is deterministic: the clock does not move unless you move it, ids count, and the model
says exactly what it was told to. That is what makes `tests/runtime/test_replay.py` possible, and
it is what a host needs to test its own governance and sink without a provider account.
"""

from shadow_hdk.runtime.testing.doubles import (
    AllowAuthorizer,
    FixedAuthority,
    FixedClock,
    InMemoryComponents,
    Judge,
    ListObserver,
    ListSink,
    ScriptedModel,
    make_registration,
)

__all__ = [
    "AllowAuthorizer",
    "FixedClock",
    "FixedAuthority",
    "InMemoryComponents",
    "Judge",
    "ListObserver",
    "ListSink",
    "ScriptedModel",
    "make_registration",
]
