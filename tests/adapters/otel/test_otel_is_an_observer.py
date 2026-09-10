"""The OpenTelemetry adapter, held to the observer contract (TD-004).

An observer is the one port the runtime does not wait on, which is exactly why it needs a contract:
a mistake here is silent by design. The suite asks it to accept the events that bracket every run
and one that carries an observation — the arms most likely to be forgotten by a `match` written
when the union was shorter (D20 made it eleven).
"""

from __future__ import annotations

from shadow_hdk.adapters.otel import OpenTelemetryObserver
from shadow_hdk.kernel.ports import ObserverPort
from tests.adapters.contract import ObserverPortContract
from tests.adapters.otel.conftest import RecordingTracer


class TestOpenTelemetryObserverIsAnObserverPort(ObserverPortContract):
    def port(self) -> ObserverPort:
        return OpenTelemetryObserver(tracer=RecordingTracer())
