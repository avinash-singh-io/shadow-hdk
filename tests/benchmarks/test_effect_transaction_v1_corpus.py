"""The Phase 33 evaluator is immutable; changed outcomes require a v2 corpus."""

from __future__ import annotations

import hashlib
from pathlib import Path

CORPUS = Path(__file__).with_name("effect-transaction-v1.json")
V1_SHA256 = "c6f4bbe9d4531fcf944e58d1db48442bc09e0abc894bf55f620625db4a7a708a"


def test_effect_transaction_v1_is_frozen() -> None:
    assert hashlib.sha256(CORPUS.read_bytes()).hexdigest() == V1_SHA256
