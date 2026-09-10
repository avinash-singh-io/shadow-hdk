# shadow-hdk-adapters-otel

An `ObserverPort` that exports the shape of a run — spans for runs and steps, events for refusals,
asks, spawns and holds — over the OpenTelemetry **API** alone (D28). Bring your own SDK and
exporter; with none configured the observer is a no-op that costs nothing and never raises.
