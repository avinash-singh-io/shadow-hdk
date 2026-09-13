"""The patterns the framework ships — now files, read from `library/` (D17).

This module stays so that `single` is importable as it always was, but it is no longer where the
pattern *lives*: the file is. A team adds its own by writing one and calling `load_pattern`, which
is the same call this uses (`09` §5).
"""

from __future__ import annotations

from shadow_hdk.adapters.agent.loader import shipped

single = shipped()["single"]
"""One reasoning loop over its tools. No `compose`, so the model cannot change its own shape —
which is what makes a deterministic one-agent product possible on this runtime."""

SINGLE_ROLE = single.system

__all__ = ["SINGLE_ROLE", "single"]
