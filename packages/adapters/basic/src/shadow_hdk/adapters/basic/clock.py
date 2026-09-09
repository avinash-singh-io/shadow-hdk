"""The clock the runtime has when nobody is replaying it."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from shadow_hdk.kernel.ports import ClockPort


class SystemClock(ClockPort):
    def now(self) -> str:
        return datetime.now(UTC).isoformat()

    def new_id(self) -> str:
        return uuid.uuid4().hex
