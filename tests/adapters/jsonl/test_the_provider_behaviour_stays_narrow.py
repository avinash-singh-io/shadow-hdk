"""TD-024's distinction, held to exactly its own case.

As of 0.49.0 this kit's side is complete: the catalogue is correct whenever it is asked, before a
run as well as inside one, and a run whose catalogue was never read says so. So a request that
carried none of the tools we had just answered with is the provider's doing, not the kit's — a
measured behaviour of one environment's SDK.

That attribution is only worth anything while it is narrow, which is why it is a function with its
own controls rather than a condition inline in a real-SDK proof. Inside that proof the branch is
dead wherever the behaviour does not occur, so mutating it there would prove nothing and the
narrowness would be asserted instead of measured. These need no SDK and run everywhere.
"""

from typing import Any

import pytest

from tests.adapters.jsonl.test_real_codex_governance import composed_without_what_it_was_offered

OFFERED = ("read_file",)
FAILED = ["StopIteration: ..."]


def a_request(*, with_tools: bool) -> list[Any]:
    server: dict[str, Any] = {"type": "function", "name": "mcp__shadow_hdk"}
    if with_tools:
        server["tools"] = [{"name": "read_file"}]
    return [{"tools": [server]}]


def test_the_case_it_is_meant_to_cover() -> None:
    assert composed_without_what_it_was_offered(OFFERED, FAILED, False, a_request(with_tools=False))


@pytest.mark.parametrize(
    "why, offered, failures, unreached, captures",
    [
        (
            "nothing failed, so there is nothing to attribute",
            OFFERED,
            [],
            False,
            a_request(with_tools=False),
        ),
        (
            "we answered with nothing, which is this kit's own defect and not the provider's",
            (),
            FAILED,
            False,
            a_request(with_tools=False),
        ),
        (
            "the catalogue was never read, which the run already names itself",
            OFFERED,
            FAILED,
            True,
            a_request(with_tools=False),
        ),
        (
            "the request did carry the tools, so whatever failed is something else entirely",
            OFFERED,
            FAILED,
            False,
            a_request(with_tools=True),
        ),
        ("no request was captured at all, which is a different break", OFFERED, FAILED, False, []),
    ],
)
def test_everything_else_is_still_a_failure(
    why: str, offered: tuple[str, ...], failures: list[str], unreached: bool, captures: list[Any]
) -> None:
    assert composed_without_what_it_was_offered(offered, failures, unreached, captures) is False, (
        why
    )
