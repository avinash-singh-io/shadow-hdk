"""The coder's thread is the harness's (Phase 26): `a_thread` lives in `shadow_hdk.serve`.

Kept as a module so `python -m examples.coder` reads as it did; nothing of the composition is
here. A product imports the same name from the package.
"""

from __future__ import annotations

from shadow_hdk.serve import a_thread

__all__ = ["a_thread"]
