"""Where effects land, with a mode (D48). Local on the OS sandbox (D49); isolated in a box somebody
else built, behind the backend seam (D50)."""

from shadow_hdk.adapters.environment.backends import Box, IsolationBackend, prove_box
from shadow_hdk.adapters.environment.local import (
    LocalEnvironment,
    LocalSandbox,
    local_sandbox,
    local_sandboxes,
)
from shadow_hdk.adapters.environment.sandbox import SandboxEnvironment

__all__ = [
    "Box",
    "IsolationBackend",
    "LocalEnvironment",
    "LocalSandbox",
    "SandboxEnvironment",
    "local_sandbox",
    "local_sandboxes",
    "prove_box",
]
