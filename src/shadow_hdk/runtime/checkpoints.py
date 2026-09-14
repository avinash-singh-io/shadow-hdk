"""A parked run behind a port of ours (D93): the runtime library's checkpointer over `RunStore`.

The runtime parks a run in LangGraph's checkpointer and resumes it from there (D57, D80). That
contract is the library's — `BaseCheckpointSaver`, a dozen methods and a serialiser — and a
product not on SQLite or Postgres had to implement it. `saver_over(run_store)` is that
checkpointer over the kernel's four-method port: every checkpoint and every pending write is a
row of bytes under the run's id, serialised by the library's own serde, so a product keeps
parked runs in its own tables and knows nothing of the library. The shipped SQLite and Postgres
savers stay the fast path; `InMemoryRunStore` is for tests and a process that keeps nothing.

Keys, under a run id: `cp/<ns>/<checkpoint_id>` — the checkpoint, its metadata and its parent;
`wr/<ns>/<checkpoint_id>/<task_id>/<index>` — one pending write. Checkpoint ids order by time,
which is what `list` and *latest* rely on, as the library's own savers do.
"""

from __future__ import annotations

import base64
import json
from collections import defaultdict
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
    get_checkpoint_metadata,
)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from shadow_hdk.kernel.ports import RunStore


class InMemoryRunStore(RunStore):
    """A `RunStore` that lives as long as the process — tests, and the memory url's default."""

    def __init__(self) -> None:
        self._rows: dict[str, dict[str, bytes]] = defaultdict(dict)

    async def put(self, run_id: str, key: str, blob: bytes) -> None:
        self._rows[run_id][key] = bytes(blob)

    async def get(self, run_id: str, key: str) -> bytes | None:
        return self._rows[run_id].get(key)

    async def list(self, run_id: str, *, prefix: str = "") -> tuple[tuple[str, bytes], ...]:
        rows = self._rows.get(run_id, {})
        return tuple((k, rows[k]) for k in sorted(rows) if k.startswith(prefix))

    async def delete(self, run_id: str) -> None:
        self._rows.pop(run_id, None)


def _packed(typed: tuple[str, bytes]) -> list[str]:
    kind, raw = typed
    return [kind, base64.b64encode(raw).decode("ascii")]


def _unpacked(packed: Any) -> tuple[str, bytes]:
    kind, raw = packed
    return str(kind), base64.b64decode(raw)


class SaverOverRunStore(BaseCheckpointSaver[str]):
    """LangGraph's checkpointer over a `RunStore`. Async only, like the library's own database
    savers: the runtime drives graphs with `ainvoke`, and a synchronous call says so."""

    def __init__(self, store: RunStore) -> None:
        super().__init__(serde=JsonPlusSerializer())
        self._store = store

    # ------------------------------------------------------------------ the sync half refuses

    def get_tuple(self, config: Any) -> CheckpointTuple | None:
        raise NotImplementedError("use the async methods: this saver runs on a RunStore")

    def list(
        self,
        config: Any,
        *,
        filter: dict[str, Any] | None = None,
        before: Any = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        raise NotImplementedError("use the async methods: this saver runs on a RunStore")

    def put(
        self,
        config: Any,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> Any:
        raise NotImplementedError("use the async methods: this saver runs on a RunStore")

    def put_writes(
        self, config: Any, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = ""
    ) -> None:
        raise NotImplementedError("use the async methods: this saver runs on a RunStore")

    def delete_thread(self, thread_id: str) -> None:
        raise NotImplementedError("use the async methods: this saver runs on a RunStore")

    # ------------------------------------------------------------------ the async half

    async def aget_tuple(self, config: Any) -> CheckpointTuple | None:
        run_id = str(config["configurable"]["thread_id"])
        ns = str(config["configurable"].get("checkpoint_ns", ""))
        checkpoint_id = get_checkpoint_id(config)
        if checkpoint_id:
            raw = await self._store.get(run_id, f"cp/{ns}/{checkpoint_id}")
            if raw is None:
                return None
        else:
            rows = await self._store.list(run_id, prefix=f"cp/{ns}/")
            if not rows:
                return None
            key, raw = rows[-1]  # ids order by time: the last key is the latest checkpoint
            checkpoint_id = key.rsplit("/", 1)[1]
        return await self._tuple(run_id, ns, checkpoint_id, raw)

    async def _tuple(self, run_id: str, ns: str, checkpoint_id: str, raw: bytes) -> CheckpointTuple:
        saved = json.loads(raw)
        writes = await self._store.list(run_id, prefix=f"wr/{ns}/{checkpoint_id}/")
        pending = []
        for _key, blob in writes:
            write = json.loads(blob)
            pending.append(
                (
                    str(write["task_id"]),
                    str(write["channel"]),
                    self.serde.loads_typed(_unpacked(write["value"])),
                )
            )
        parent = saved.get("parent")
        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": run_id,
                    "checkpoint_ns": ns,
                    "checkpoint_id": checkpoint_id,
                }
            },
            checkpoint=self.serde.loads_typed(_unpacked(saved["checkpoint"])),
            metadata=self.serde.loads_typed(_unpacked(saved["metadata"])),
            pending_writes=pending,
            parent_config=(
                {
                    "configurable": {
                        "thread_id": run_id,
                        "checkpoint_ns": ns,
                        "checkpoint_id": parent,
                    }
                }
                if parent
                else None
            ),
        )

    async def alist(
        self,
        config: Any,
        *,
        filter: dict[str, Any] | None = None,
        before: Any = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        if config is None:
            return
        run_id = str(config["configurable"]["thread_id"])
        ns = config["configurable"].get("checkpoint_ns")
        wanted = get_checkpoint_id(config)
        before_id = get_checkpoint_id(before) if before else None
        rows = await self._store.list(run_id, prefix="cp/")
        count = 0
        for key, raw in reversed(rows):
            _cp, key_ns, checkpoint_id = key.split("/", 2)
            if ns is not None and key_ns != ns:
                continue
            if wanted and checkpoint_id != wanted:
                continue
            if before_id and checkpoint_id >= before_id:
                continue
            found = await self._tuple(run_id, key_ns, checkpoint_id, raw)
            metadata = found.metadata or {}
            if filter and not all(metadata.get(k) == v for k, v in filter.items()):
                continue
            if limit is not None and count >= limit:
                return
            count += 1
            yield found

    async def aput(
        self,
        config: Any,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> Any:
        run_id = str(config["configurable"]["thread_id"])
        ns = str(config["configurable"].get("checkpoint_ns", ""))
        row = {
            "checkpoint": _packed(self.serde.dumps_typed(checkpoint)),
            "metadata": _packed(self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))),
            "parent": config["configurable"].get("checkpoint_id"),
        }
        await self._store.put(run_id, f"cp/{ns}/{checkpoint['id']}", json.dumps(row).encode())
        return {
            "configurable": {
                "thread_id": run_id,
                "checkpoint_ns": ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    async def aput_writes(
        self, config: Any, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = ""
    ) -> None:
        run_id = str(config["configurable"]["thread_id"])
        ns = str(config["configurable"].get("checkpoint_ns", ""))
        checkpoint_id = str(config["configurable"]["checkpoint_id"])
        for index, (channel, value) in enumerate(writes):
            slot = WRITES_IDX_MAP.get(channel, index)
            key = f"wr/{ns}/{checkpoint_id}/{task_id}/{slot:+d}"
            # A write already there is kept, as the library's savers keep it: the special
            # channels (errors, interrupts, resumes) overwrite, ordinary writes do not.
            if slot >= 0 and await self._store.get(run_id, key) is not None:
                continue
            row = {
                "task_id": task_id,
                "channel": channel,
                "value": _packed(self.serde.dumps_typed(value)),
                "task_path": task_path,
            }
            await self._store.put(run_id, key, json.dumps(row).encode())

    async def adelete_thread(self, thread_id: str) -> None:
        await self._store.delete(thread_id)


def saver_over(store: RunStore) -> SaverOverRunStore:
    """LangGraph's checkpointer over a `RunStore` (D93)."""
    return SaverOverRunStore(store)


__all__ = ["InMemoryRunStore", "SaverOverRunStore", "saver_over"]
