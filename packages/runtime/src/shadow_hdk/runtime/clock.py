"""The clock the runtime has when nobody is replaying it.

**It lives in the runtime, not in an adapter** (TD-003). The wire needs a default clock and reached
into `adapters.basic` for one — an undeclared dependency, so `shadow-hdk-wire` installed on its
own raised `ImportError` the first time a host called `ports()`. That is the stands-alone rule one
layer up, and the remedy is the one the rule already names: what two layers need moves below both.

`adapters.basic` re-exports it, so every existing `from shadow_hdk.adapters.basic import
SystemClock` still works. There is nothing adapter-shaped about reading the wall clock — no vendor,
no protocol, no host decision — which is why it can move without an argument about layering.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from shadow_hdk.kernel.ports import ClockPort

__all__ = ["SystemClock"]


class SystemClock(ClockPort):
    def now(self) -> str:
        return datetime.now(UTC).isoformat()

    def new_id(self) -> str:
        return uuid.uuid4().hex
