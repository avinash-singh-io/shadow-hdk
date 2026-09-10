"""The clock the runtime has when nobody is replaying it.

**Moved to `shadow_hdk.runtime.clock`** (TD-003) and re-exported here, because the wire needs a
default clock and may not import an adapter to get one. Every existing import keeps working; new
code may take it from either place.
"""

from __future__ import annotations

from shadow_hdk.runtime.clock import SystemClock

__all__ = ["SystemClock"]
