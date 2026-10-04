# H8 — confirmed before implementation, 2026-10-04

`_Turnwise` initializes Usage with only three counters, accumulates only input/output/cost in
charge, and emits only those three in finished. `_ModelSession._usage` reconstructs only the same
three. Cache read/write fields already exist on Usage (D141), on model responses and streamed
chunks, and the runtime's step meter already reads both from output usage. The loss is therefore
in the model-loop adapter, not a new contract or missing runtime mechanism. BUG-240, P1.

Repair initialization, aggregation, output and reconstruction together. Known zero stays zero;
unknown on either cache axis absorbs later known values, just like the existing usage counters.
Prove multi-call aggregation on the actual component loop and model-agent thread, including
thread record persistence and existing wire events/listing. Use installed artifacts as well.
A separate 0.47.3 patch after 0.47.2, no new contract/Pins row (D9). D190: a coding tool,
a support desk and a research assistant would each use accurate model-usage accounting.

## Verification after implementation

Nine new cases failed before production changes; the all-unknown wire case already passed.
Ten now pass on source and on the installed wheel outside checkout. Twenty targeted mutations
bite; the meter mutations target LeaseMeter.settle, the actual thread path, rather than count_tokens.
Source bytecode was cleared before every mutant and writes disabled (TD-021). All 55 previous
train checks were re-run under the same precaution and bite. Full gate: 2,274 passed, 8 skipped, 24 deselected; lint/format/types clean with disposable PostgreSQL enabled. Kit wheel/sdist
build; all 165 package Python sources match the wheel; schema/client regeneration has no drift.
