"""H6: the existing wire store path delivers named mode context to shared assembly."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from shadow_hdk.adapters.basic.store import SqliteStore
from shadow_hdk.adapters.modes.registry import mode_from_document, store_modes
from shadow_hdk.kernel.providers import carried_by, framed
from shadow_hdk.wire.threads import ThreadMethods

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "fragments, expected",
    [
        (
            [
                {"name": "style", "text": "Be precise", "source": "product"},
                {"name": "scope", "text": "Only this task"},
            ],
            '<context name="style" source="product">\nBe precise\n</context>\n\n'
            '<context name="scope">\nOnly this task\n</context>',
        ),
        ([], ""),
    ],
)
async def test_wire_rows_reach_the_shared_prompt_assembler(
    tmp_path: Path, fragments: list[dict[str, str]], expected: str
) -> None:
    store = SqliteStore(tmp_path / "rows.sqlite")
    methods = ThreadMethods(
        SimpleNamespace(serves=lambda *args: None),
        cast(Any, SimpleNamespace(store=store)),
        None,
    )
    await methods._store_put(
        {
            "collection": "modes",
            "key": "custom",
            "row": {
                "id": "custom",
                "policy": "workspace-write",
                "behaviour": {"fragments": fragments},
            },
        }
    )
    mode = (await store_modes(store).modes())[0]
    assert framed(carried_by(mode.behaviour)) == expected


@pytest.mark.parametrize(
    "fragment",
    [{"text": "Missing name"}, {"name": "Missing text"}, {"name": 42, "text": "Wrong type"}],
)
def test_malformed_fragment_documents_are_refused(fragment: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="fragments|name|text"):
        mode_from_document(
            {"id": "bad", "policy": "workspace-write", "behaviour": {"fragments": [fragment]}},
            source="file",
        )


async def test_bad_stored_fragments_are_reported_before_assembly(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "rows.sqlite")
    await store.put(
        "modes", "bad", {"id": "bad", "policy": "workspace-write", "behaviour": {"fragments": [{}]}}
    )
    modes = store_modes(store)
    assert (await modes.modes(), "modes/bad:" in " ".join(await modes.problems())) == ((), True)
