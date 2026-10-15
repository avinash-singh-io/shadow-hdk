"""The one gap declared in the governance control, held to exactly its own case (TD-023).

A declared gap is only honest while it is narrow. This one covers a single situation — the kit
answered a listing carrying tools and the provider composed its request without them, having read
the catalogue too late to use it — and it must cover nothing else, because everything else is a
real failure that has to stay a failure.

Its own controls live here rather than beside the real-SDK proof, so the narrowness is measured
instead of asserted: inside that proof the branch is dead wherever the gap does not occur, so
mutating it there proves nothing. These run everywhere and need no SDK.
"""

from typing import Any

import pytest

from tests.adapters.jsonl.test_real_codex_governance import read_too_late

OFFERED = ("read_file",)
FAILED = ["StopIteration: ..."]
EMPTY_LISTING: list[Any] = [{"tools": {"name": "mcp__shadow_hdk"}}]


def a_request(*, with_tools: bool) -> list[Any]:
    """What the provider sent, as the control captured it: a server entry either holding the
    governed tools or holding nothing."""
    server: dict[str, Any] = {"type": "function", "name": "mcp__shadow_hdk"}
    if with_tools:
        server["tools"] = [{"name": "read_file"}]
    return [{"tools": [server]}]


def test_the_gap_it_is_meant_to_cover() -> None:
    assert read_too_late(OFFERED, FAILED, False, a_request(with_tools=False)) is True


@pytest.mark.parametrize(
    "why, offered, failures, unreached, captures",
    [
        (
            "nothing failed, so there is nothing to excuse",
            OFFERED,
            [],
            False,
            a_request(with_tools=False),
        ),
        (
            "we offered nothing, which is this side's own defect",
            (),
            FAILED,
            False,
            a_request(with_tools=False),
        ),
        (
            "the catalogue was never read, which the kit already names",
            OFFERED,
            FAILED,
            True,
            a_request(with_tools=False),
        ),
        (
            "the provider did carry the tools, so the failure is something else",
            OFFERED,
            FAILED,
            False,
            a_request(with_tools=True),
        ),
        ("no request was captured at all, which is a different break", OFFERED, FAILED, False, []),
    ],
)
def test_everything_else_still_fails(
    why: str, offered: tuple[str, ...], failures: list[str], unreached: bool, captures: list[Any]
) -> None:
    assert read_too_late(offered, failures, unreached, captures) is False, why
