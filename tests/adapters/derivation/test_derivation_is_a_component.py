"""The derivation adapter, held to the component contract (TD-004)."""

from __future__ import annotations

from pydantic import JsonValue

from shadow_hdk.adapters.derivation import DerivationComponents
from shadow_hdk.kernel.components import RegistrationId
from shadow_hdk.kernel.ports import ComponentPort
from tests.adapters.contract import ComponentPortContract

A_TABLE: JsonValue = {
    "columns": {"amount": "number"},
    "units": {"amount": "kg"},
    "row_unit": "row",
    "rows": [{"amount": "1"}, {"amount": "2"}],
}


class TestDerivationComponentsIsAComponentPort(ComponentPortContract):
    def port(self) -> ComponentPort:
        return DerivationComponents()

    def valid_call(self) -> tuple[RegistrationId, JsonValue]:
        return "derive", {"table": A_TABLE, "ground": {"sum": "amount"}}
