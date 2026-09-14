"""An Item carries one canonical, bounded projection of Invoked.inputs."""

from __future__ import annotations

import json

from pydantic import TypeAdapter

from shadow_hdk.kernel import Completed, Invoked, Observed
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.runtime.items import ITEM_INPUT_BYTES, Item, items


def _invoked(inputs: object) -> Invoked:
    return Invoked(run_id="run", seq=1, at="t", step="step", component="tool", inputs=inputs)  # type: ignore[arg-type]


def test_the_fold_keeps_canonical_json_inputs_and_the_contract_round_trips_them() -> None:
    payload = {"z": [1, True, None], "a": {"word": "café"}}
    (item,) = items(
        [
            _invoked(payload),
            Observed(run_id="run", seq=2, at="t", step="step", observation=Completed("ok")),
        ]
    )

    assert item.inputs == payload
    assert load(dump(item, Item), Item) == item
    TypeAdapter(Item).validate_json(dump(item, Item))


def test_an_over_limit_projection_is_explicit_instead_of_silently_cut() -> None:
    payload = {"text": "x" * ITEM_INPUT_BYTES}
    (item,) = items([_invoked(payload)])
    encoded = json.dumps(item.inputs, sort_keys=True, separators=(",", ":")).encode()

    assert len(encoded) <= ITEM_INPUT_BYTES
    assert item.inputs == {
        "$shadow": {
            "kind": "omitted",
            "reason": "too_large",
            "bytes": len(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()),
        }
    }
