"""A derivation answers rather than raises, and the same numbers give the same identity (BUG-013).

Four claims, each reproduced against the code before it was written. Two of them correct the audit's
row rather than merely implementing it, and the corrections are the interesting part.

**Total.** `values.py` opens by promising it: *No operation raises on its inputs.* It was not true —
`_fix` quantizes to twelve places under a 34-digit context, and a magnitude that does not fit raises
`InvalidOperation`. `component.py` called `evaluate` outside its own `try`, so the exception left
`invoke` entirely, which D7 says a component may never do.

**Canonical.** `"1"`, `"1.0"` and `"1.00"` are one quantity spelled three ways and produced three
different fingerprints, because the tree was built by `str()`-ing the raw `Decimal`. A fingerprint
that changes with spelling cannot answer *have I derived this before*.

**Normalised.** The audit filed this as NFC-versus-NFD in a *unit*, and there it makes no
difference. In a **cell** it does, and it is not a hashing problem at all — it is a **wrong
answer**: the same word in two normal forms is two values, so a count of them came back 1 and 0.

**Typed.** `Table.rows` has been annotated `Mapping[str, str | bool]` since Phase 12 and nothing
enforced it, so an `int` or a `float` went straight through. The arithmetic survived it — `0.1` and
`"0.1"` both sum to `0.300000000000`, because the value goes through `str()` — but the **fingerprint
did not**, so two identical tables had two identities.
"""

from __future__ import annotations

import unicodedata
from typing import Any

from pydantic import JsonValue

from shadow_hdk.adapters.derivation import DerivationComponents
from shadow_hdk.kernel import Completed, Failed, Observation

NFC = unicodedata.normalize("NFC", "café")
NFD = unicodedata.normalize("NFD", "café")


def numbers(rows: list[JsonValue], unit: str = "kg") -> JsonValue:
    return {
        "columns": {"amount": "number"},
        "units": {"amount": unit},
        "row_unit": "row",
        "rows": rows,
    }


def words(rows: list[JsonValue]) -> JsonValue:
    return {"columns": {"name": "text"}, "units": {}, "row_unit": "row", "rows": rows}


async def derive(ground: JsonValue, table: JsonValue) -> Observation:
    components = DerivationComponents()
    registrations = await components.registrations()
    return await components.invoke(registrations[0].id, {"table": table, "ground": ground})


def claim(observation: Observation) -> dict[str, Any]:
    assert isinstance(observation, Completed), observation
    assert isinstance(observation.output, dict)
    return dict(observation.output)


# ------------------------------------------------------------------ total


async def test_a_magnitude_too_large_to_hold_is_answered_not_raised() -> None:
    """`1e22` quantized to twelve places needs more digits than the context has. It raised
    `InvalidOperation` straight out of `invoke` — past the component boundary D7 draws, where the
    runtime can only report it as a crash rather than as something the agent can reason about."""
    observation = await derive({"lit": "1e22"}, numbers([{"amount": "1"}]))
    answer = claim(observation)

    assert answer["value"] is None
    assert answer["indeterminate"] is not None
    assert answer["indeterminate"]["reason"] == "out_of_range"


async def test_a_product_too_large_to_hold_is_answered_not_raised() -> None:
    """The same thing arrived at by arithmetic rather than written down, which is the case a caller
    cannot avoid by checking its own inputs."""
    answer = claim(
        await derive({"mul": [{"lit": "1e15"}, {"lit": "1e15"}]}, numbers([{"amount": "1"}]))
    )

    assert answer["value"] is None
    assert answer["indeterminate"]["reason"] == "out_of_range"


async def test_an_infinite_literal_is_answered_not_raised() -> None:
    """`Decimal` accepts `Infinity` happily; the quantizer does not."""
    answer = claim(await derive({"lit": "Infinity"}, numbers([{"amount": "1"}])))

    assert answer["value"] is None
    assert answer["indeterminate"]["reason"] == "out_of_range"


async def test_the_reason_says_which_value_could_not_be_held() -> None:
    """An indeterminate that only says *out_of_range* sends its reader back to the inputs to guess
    which one. Every other reason in this engine names its cause."""
    answer = claim(await derive({"lit": "1e22"}, numbers([{"amount": "1"}])))

    assert "1E+22" in answer["indeterminate"]["detail"]


# ------------------------------------------------------------------ canonical


async def test_the_same_number_spelled_three_ways_has_one_fingerprint() -> None:
    """The identity of a derivation is the identity of what it derived from, and `"1"`, `"1.0"`
    and `"1.00"` are one quantity. Measured before: three fingerprints."""
    table = numbers([{"amount": "1"}])
    fingerprints = {
        spelling: claim(await derive({"lit": spelling}, table))["fingerprint"]
        for spelling in ("1", "1.0", "1.00")
    }

    assert len(set(fingerprints.values())) == 1, fingerprints


async def test_two_numbers_that_differ_still_differ() -> None:
    """What a canonical form must not do: collapse quantities that are not equal. Twelve places is
    the engine's own scale, so a difference it can represent is a difference it must keep."""
    table = numbers([{"amount": "1"}])
    one = claim(await derive({"lit": "1"}, table))["fingerprint"]
    almost = claim(await derive({"lit": "1.000000000001"}, table))["fingerprint"]

    assert one != almost


async def test_a_cell_spelled_differently_has_one_fingerprint() -> None:
    """The same claim from the table's side rather than the ground's."""
    plain = claim(await derive({"sum": "amount"}, numbers([{"amount": "2"}])))
    padded = claim(await derive({"sum": "amount"}, numbers([{"amount": "2.00"}])))

    assert plain["fingerprint"] == padded["fingerprint"]
    assert plain["value"] == padded["value"]


# ------------------------------------------------------------------ normalised


async def test_the_same_word_in_two_normal_forms_counts_the_same() -> None:
    """**The most serious part, and the one the audit put in the wrong place.** Not a hash that
    differs — a count that is wrong. `café` composed and `café` decomposed are the same word to
    every reader and two different strings to `==`, so a cell typed on one keyboard and a query
    typed on another silently answer zero.
    """
    counting: JsonValue = {"count_where": {"col": "name", "eq": NFC}}
    composed = claim(await derive(counting, words([{"name": NFC}])))
    decomposed = claim(await derive(counting, words([{"name": NFD}])))

    assert composed["value"] == decomposed["value"]
    assert composed["value"] != "0E-12", "the arrangement failed: neither form matched"


async def test_normalisation_reaches_the_query_as_well_as_the_cell() -> None:
    """Both sides, or it is a coin toss which one was typed how."""
    answer = claim(
        await derive({"count_where": {"col": "name", "eq": NFD}}, words([{"name": NFC}]))
    )

    assert answer["value"] != "0E-12"


async def test_two_normal_forms_give_one_fingerprint() -> None:
    """And the identity follows the value, as it must — a table is the same table."""
    counting: JsonValue = {"count_where": {"col": "name", "eq": NFC}}
    composed = claim(await derive(counting, words([{"name": NFC}])))
    decomposed = claim(await derive(counting, words([{"name": NFD}])))

    assert composed["fingerprint"] == decomposed["fingerprint"]


# ------------------------------------------------------------------ typed


async def test_a_number_cell_that_is_not_a_string_is_refused() -> None:
    """`Table.rows` says `Mapping[str, str | bool]` and has since Phase 12. Nothing enforced it.

    Refused rather than coerced, and the reason is the engine's whole claim: a JSON number has
    already been through a float by the time it arrives, so accepting one means the exactness this
    engine promises started from a value somebody else had already rounded. A string is the only
    JSON form that carries a decimal intact.
    """
    observation = await derive({"sum": "amount"}, numbers([{"amount": 1}]))

    assert isinstance(observation, Failed)
    assert "amount" in observation.error
    assert '"1"' in observation.error, f"the refusal does not say what to send: {observation.error}"


async def test_a_float_cell_is_refused_by_the_same_rule() -> None:
    """The one that actually loses information, and the one the audit was pointing at."""
    observation = await derive({"sum": "amount"}, numbers([{"amount": 0.1}]))

    assert isinstance(observation, Failed)
    assert "amount" in observation.error


async def test_a_boolean_cell_is_still_accepted() -> None:
    """`str | bool`, not `str`. A flag column is a real thing and a JSON boolean carries it exactly,
    which is the whole test for whether a form is allowed here."""
    table: JsonValue = {
        "columns": {"ok": "bool"},
        "units": {},
        "row_unit": "row",
        "rows": [{"ok": True}, {"ok": False}],
    }

    answer = claim(await derive({"count": "ok"}, table))

    assert answer["value"] == "2.000000000000"


async def test_the_refusal_names_the_row_it_found() -> None:
    """A table of two thousand rows and a message that says only *a cell is wrong* is a message
    that costs an afternoon."""
    observation = await derive(
        {"sum": "amount"}, numbers([{"amount": "1"}, {"amount": "2"}, {"amount": 3}])
    )

    assert isinstance(observation, Failed)
    assert "2" in observation.error, f"the refusal does not name the row: {observation.error}"


async def test_the_component_answers_even_if_the_engine_stops_being_total(
    monkeypatch: Any,
) -> None:
    """D7's boundary, held independently of what is behind it.

    Found by a mutation that survived: moving `evaluate` back outside the component's `try` broke
    nothing, because `evaluate` is total now and the guard had nothing to catch. That makes the
    guard untested rather than unnecessary — the inside can change, and the boundary is the thing
    that must not.

    So the engine is made to raise on purpose. A component may return `Failed`; it may not throw.
    """
    from shadow_hdk.adapters.derivation import component as under_test

    def unwell(*_args: object, **_kwargs: object) -> object:
        raise ArithmeticError("the engine stopped being total")

    monkeypatch.setattr(under_test, "evaluate", unwell)
    observation = await derive({"lit": "1"}, numbers([{"amount": "1"}]))

    assert isinstance(observation, Failed)
    assert "stopped being total" in observation.error
