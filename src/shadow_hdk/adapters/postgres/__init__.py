"""The record on Postgres (D79): a `Store`, a `ThreadStore` and a checkpointer over one url.

The same three contracts the sqlite adapters hold, for a product whose harness runs as one app
server behind every surface and keeps its state where the rest of its state is. Behind the
`postgres` extra — `pip install 'shadow-hdk[postgres]'` — and named in the refusal when it is
not installed, the way the sandbox names its own.
"""

from shadow_hdk.adapters.postgres.checkpoints import postgres_checkpointer
from shadow_hdk.adapters.postgres.effects import PostgresEffectJournal
from shadow_hdk.adapters.postgres.store import PostgresStore
from shadow_hdk.adapters.postgres.threads import PostgresThreads

__all__ = ["PostgresEffectJournal", "PostgresStore", "PostgresThreads", "postgres_checkpointer"]
