"""D: chooser text reaches the existing wire reply without replacing role instructions."""

from types import SimpleNamespace
from typing import Any, cast

import pytest

from shadow_hdk.adapters.agent.loader import pattern_from
from shadow_hdk.adapters.agent.pattern import Pattern
from shadow_hdk.adapters.agent.patterns import PatternRegistry, store_patterns
from shadow_hdk.wire.threads import ThreadMethods

pytestmark = pytest.mark.anyio

ROW = {"name": "reviewer", "system": "ROLE\nFollow the procedure."}


class Store:
    def __init__(self, row: dict[str, Any]) -> None:
        self.row = row

    async def version(self, collection: str) -> int:
        return 1

    async def list(self, collection: str) -> list[tuple[str, Any]]:
        return [("reviewer", self.row)]


def test_the_loader_keeps_presentation_and_instructions_separate() -> None:
    row = pattern_from({**ROW, "description": "Review a proposal"}, where="row")
    assert (row.description, row.system) == ("Review a proposal", ROW["system"])


def test_direct_patterns_default_to_the_existing_derivation() -> None:
    assert Pattern(name="reviewer", system="ROLE").description is None


@pytest.mark.parametrize(
    "extra, line",
    [
        ({"description": "Review a proposal"}, "Review a proposal"),
        ({"description": ""}, ""),
        ({}, "ROLE"),
        ({"description": None}, "ROLE"),
    ],
)
async def test_stored_descriptions_and_fallbacks_reach_agents_list(
    extra: dict[str, Any], line: str
) -> None:
    registry = PatternRegistry((store_patterns(Store({**ROW, **extra})),), include_shipped=False)
    methods = SimpleNamespace(_host_or_raise=lambda: SimpleNamespace(patterns=registry))
    reply = await ThreadMethods._agents_list(cast(ThreadMethods, methods), {})
    assert reply == {"agents": [{"name": "reviewer", "description": line}]}
