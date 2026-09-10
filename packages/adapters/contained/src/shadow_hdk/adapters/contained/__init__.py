"""A sandbox that proves it is contained, or refuses to exist."""

from shadow_hdk.adapters.contained.doubles import FakeIsolation
from shadow_hdk.adapters.contained.sandbox import (
    ContainedSandbox,
    IsolationBackend,
    NotContained,
    Proof,
)

__all__ = ["ContainedSandbox", "FakeIsolation", "IsolationBackend", "NotContained", "Proof"]
