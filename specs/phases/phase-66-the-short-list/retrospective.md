---
type: Retrospective
phase: phase-66-the-short-list
status: complete
---

# Phase 66 — release train complete

All six releases are merged and published, and their seven-file and fresh-install evidence is
recorded in `evidence/published-*.json` and `published-*-index-check.txt`. Local full gates ran
on each merged tree before its tag. Each clean-runner CI and publication workflow passed.
The wire test had depended on an installed vendor CLI; a guarded red reproduction exposed it,
and a handed CLI port fixed the test without changing package code. Both assertions kill their
mutations. Index propagation delayed some fresh installations; only the final install job was
restarted for 0.46.0, 0.47.1 and 0.47.2, then passed. TD-021 remains explicitly open with its workaround.

## Historical checkpoint notes

The first train checkpoint adds E, ships the previously gated unreleased changes and applies the
mandated DDL-free PostgreSQL default. C, D and H6–H8 remain for separate releases. This is release
verification evidence, not a claim that the phase is complete or that the candidate is published.

## What held

The existing model loop supplies binding, dependency checking and instruction delivery. The host
only resolves a stored opaque name and wires that existing mechanism. Unsupported pre-binding is
reported; governed skill choosing still works on CLI providers. No new decision was needed.

D190: a coding tool, a support desk and a research assistant would each use this. The generic
runtime only merges opaque unsupported contributions; the adapter names the binding. No operation
name was added to kernel or runtime. D184's migration table was updated before this checkpoint.

## What the mutations found

A direct Pattern default was not initially covered; an assertion now catches its mutation. The
internal pool default was redundant because public adapters supply the flag explicitly, so the
redundant default was removed. All twenty retained mutations bite, including procedure text being
lost, the stored binding being ignored, dependency checking being bypassed, reporting being lost,
DDL being executed by default and reopen skipping verification.

## Verification Evidence

Fresh verification on 2026-10-04:

- Baseline: 2,200 passed, 29 skipped, 24 deselected; lint, format and strict types passed.
- E started red: eight failed on the missing stored-row support. Reporting separately started red
  with its fold removed. PostgreSQL defaults started red: four failed, two compatibility cases passed.
- New targeted tests: 17 passed. Disposable PostgreSQL 16 server database/store checks: 37 passed,
  including restricted-role open, close, reopen and data operations.
- Final gate: lint clean, 548 files formatted, strict types clean over 515 files;
  **2,238 passed, 8 skipped, 24 deselected**, 85 pre-existing warnings, exit 0 in 202.89 seconds.
  The skipped cases require live external accounts or tools; database cases were enabled.
- Twenty anchored mutation checks with the repository helper: all BITES. Raw results:
  [`g5-e-mutations.txt`](evidence/g5-e-mutations.txt).
- The kit wheel and sdist build. A clean virtual environment outside the checkout resolves 0.45.0;
  imports come from its installed package, and all **17 new cases pass against that wheel**.
- Published schemas and TypeScript contracts regenerated without drift. No wire property was added.
- Full gate output: [`0.45-gate.txt`](evidence/0.45-gate.txt).

## Remaining release gate

Owner protected landings, release tag and GitHub Release, then fresh-install and seven-file
publication verification for both distributions. Follow the lane P reply. Continue with C only
once this release checkpoint has landed and published; then D and individually confirmed H6–H8.

## 0.46.0 checkpoint — C, phase still open

The owner authorized preparation of the remaining separate checkpoints without waiting for
publication. This supersedes the earlier waiting instruction; each candidate freezes independently
and must land and publish parent-first. C uses the approved existing PlanLimits parser and existing
child admission. No new decision, kernel type or port was required. D and H6–H8 remain.

### Verification Evidence

Fresh verification on 2026-10-04: lint clean, 549 files formatted, strict types clean over 516
files; **2,248 passed, 8 skipped, 24 deselected**, exit 0 in 195.26 seconds, with disposable
PostgreSQL enabled. Ten C cases pass on the clean installed 0.46.0 wheel outside the checkout.
Ten mutations bite. All 165 Python source files match the wheel; schemas and TypeScript
contracts regenerate without drift. The kit wheel and sdist build. Raw gate and mutation outputs:
[`0.46-gate.txt`](evidence/0.46-gate.txt), [`g5-c-mutations.txt`](evidence/g5-c-mutations.txt).

Protected landing, release and seven-file publication verification remain with the owner.

## 0.47.0 checkpoint — D, phase still open

The approved optional description reaches the existing chooser reply; role instructions remain
separate and the absent-field fallback is preserved. This is a minor contract addition, not a
redesign. H6–H8 remain for separate source-confirmed fixes.

### Verification Evidence

Fresh verification on 2026-10-04: lint clean, 550 files formatted, strict types clean over 517
files; **2,254 passed, 8 skipped, 24 deselected**, exit 0 in 197.38 seconds, with disposable
PostgreSQL enabled. Six new D cases pass on the clean installed wheel outside the checkout.
Seven mutations bite. All 165 Python sources match the wheel; schemas and TypeScript contracts
regenerate without drift. The kit wheel and sdist build. Raw evidence:
[`0.47-gate.txt`](evidence/0.47-gate.txt), [`g5-d-mutations.txt`](evidence/g5-d-mutations.txt).

Owner landing and publication remain parent-first, one version and GitHub Release at a time.

## 0.47.1 checkpoint — H6, phase still open

Mode fragments were raw dictionaries, crashing the shared assembler. Existing wire transport
already carries rows: typed decoding repairs the contract without a new API or redesign. The
installed regression proves names, text, attribution and order; malformed rows are source problems.
H7 and H8 remain; owner publication is pending.

### Verification Evidence

Five cases failed before implementation; six pass after it, alongside all 118 mode tests.
Ten mutations bite. Full gate with disposable PostgreSQL: 2,260 passed, 8 skipped,
24 deselected; lint/format/types clean. Six new cases pass outside checkout on a fresh wheel;
all 165 Python package files match it. Wheel/sdist build; schema/client regeneration has no drift.

## 0.47.2 checkpoint — H7, phase still open

The advertised native interrupt had no configured request. Adding it alone exposed a cancelled
reader boundary: the next turn could consume the old result. Drain the interrupted terminal frame
without reporting its activity, and clear the boundary even if completion occurs during the write.
H8 remains; owner publication is pending.

### Verification Evidence

Two cases red before implementation; four final cases pass, alongside all 76 JSONL cases.
Eight targeted mutations bite. Full gate with disposable PostgreSQL: 2,264 passed, 8 skipped,
24 deselected; lint/format/types clean. Four new cases pass on the fresh installed wheel outside
checkout; 165 Python sources and the provider record match it. Source and installed live checks on
Claude Code 2.1.187 retain the process/session and receive SECOND_OK on the following turn.
Wheel/sdist build; schema/client regeneration has no drift.

## 0.47.3 checkpoint — H8; implementation complete, phase release still open

Existing cache fields were lost at the loop's accumulation/output and the model-session's
reconstruction. Repair both adapter stages, retaining zero/unknown semantics; the runtime meter
and wire already carry the fields. Mutation checking exposed TD-021 (cached bytecode can mask
same-second/same-size edits); clear source caches before each mutation and disable writes. All
previous train assertions were rechecked with this precaution. The general tool fix remains open.

### Verification Evidence

Nine cases red before implementation; ten final cases pass on source and a fresh installed wheel
outside checkout. Twenty H8 mutants and all 55 earlier train mutants bite. Full gate with disposable
PostgreSQL: 2,274 passed, 8 skipped, 24 deselected; lint/format/types clean. All 165 Python package
sources match the wheel. Wheel/sdist build; schema/client regeneration has no drift. Separate
release notes and parent-first owner commands cover every candidate. Owner landing/publication
remain, so the phase is not closed and no candidate is claimed published.


## Final Verification Evidence

### Merged-tree 0.45.0: lint, format, mypy and pytest — exit 0

Commands: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`,
`uv run pytest`, with the disposable PostgreSQL URLs configured.

```text
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/amqtt/contexts.py:192: DeprecationWarning: sys_interval is deprecated, use 'plugins' to define configuration
    warnings.warn("sys_interval is deprecated, use 'plugins' to define configuration",

tests/adapters/mqtt/test_environment.py: 3 warnings
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/amqtt/contexts.py:196: DeprecationWarning: 'auth' and 'topic-check' are deprecated, use 'plugins' to define configuration
    warnings.warn("'auth' and 'topic-check' are deprecated, use 'plugins' to define configuration",

tests/adapters/mqtt/test_environment.py: 3 warnings
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/conftest.py:41: DeprecationWarning: Loading plugins from EntryPoints is deprecated and will be removed in a future version. Use `plugins` section of config instead.

tests/adapters/mqtt/test_environment.py::test_a_broker_that_refuses_us_is_a_connection_error_naming_the_refusal
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/test_environment.py:34: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/adapters/mqtt/test_environment.py: 1 warning
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/conftest.py:70: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/adapters/mqtt/test_environment.py::test_a_broker_that_leaves_fails_the_act_and_nothing_is_sent_when_it_is_back
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/test_environment.py:65: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/kernel/test_an_adapter_is_built_once_per_type.py::test_a_type_never_seen_is_built_once_and_then_never_again
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/pydantic/type_adapter.py:677: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Defaulting to left to right union serialization - failed to get discriminator value for tagged union serialization [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Started` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Composed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Invoked` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `EffectRecorded` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Observed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Proposed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Refused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ApprovalRequested` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `InputRequested` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Spawned` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanAdmitted` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanRefused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Held` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `UsageReported` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Reasoning` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ModeChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `WorkspaceChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Ended` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    return self.serializer.to_json(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=== 2238 passed, 8 skipped, 24 deselected, 85 warnings in 188.91s (0:03:08) ====
```

### Merged-tree 0.46.0: lint, format, mypy and pytest — exit 0

Commands: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`,
`uv run pytest`, with the disposable PostgreSQL URLs configured.

```text
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/amqtt/contexts.py:192: DeprecationWarning: sys_interval is deprecated, use 'plugins' to define configuration
    warnings.warn("sys_interval is deprecated, use 'plugins' to define configuration",

tests/adapters/mqtt/test_environment.py: 3 warnings
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/amqtt/contexts.py:196: DeprecationWarning: 'auth' and 'topic-check' are deprecated, use 'plugins' to define configuration
    warnings.warn("'auth' and 'topic-check' are deprecated, use 'plugins' to define configuration",

tests/adapters/mqtt/test_environment.py: 3 warnings
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/conftest.py:41: DeprecationWarning: Loading plugins from EntryPoints is deprecated and will be removed in a future version. Use `plugins` section of config instead.

tests/adapters/mqtt/test_environment.py::test_a_broker_that_refuses_us_is_a_connection_error_naming_the_refusal
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/test_environment.py:34: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/adapters/mqtt/test_environment.py: 1 warning
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/conftest.py:70: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/adapters/mqtt/test_environment.py::test_a_broker_that_leaves_fails_the_act_and_nothing_is_sent_when_it_is_back
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/test_environment.py:65: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/kernel/test_an_adapter_is_built_once_per_type.py::test_a_type_never_seen_is_built_once_and_then_never_again
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/pydantic/type_adapter.py:677: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Defaulting to left to right union serialization - failed to get discriminator value for tagged union serialization [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Started` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Composed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Invoked` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `EffectRecorded` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Observed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Proposed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Refused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ApprovalRequested` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `InputRequested` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Spawned` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanAdmitted` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanRefused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Held` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `UsageReported` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Reasoning` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ModeChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `WorkspaceChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Ended` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    return self.serializer.to_json(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=== 2248 passed, 8 skipped, 24 deselected, 85 warnings in 198.09s (0:03:18) ====
```

### Merged-tree 0.47.0: lint, format, mypy and pytest — exit 0

Commands: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`,
`uv run pytest`, with the disposable PostgreSQL URLs configured.

```text
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/amqtt/contexts.py:192: DeprecationWarning: sys_interval is deprecated, use 'plugins' to define configuration
    warnings.warn("sys_interval is deprecated, use 'plugins' to define configuration",

tests/adapters/mqtt/test_environment.py: 3 warnings
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/amqtt/contexts.py:196: DeprecationWarning: 'auth' and 'topic-check' are deprecated, use 'plugins' to define configuration
    warnings.warn("'auth' and 'topic-check' are deprecated, use 'plugins' to define configuration",

tests/adapters/mqtt/test_environment.py: 3 warnings
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/conftest.py:41: DeprecationWarning: Loading plugins from EntryPoints is deprecated and will be removed in a future version. Use `plugins` section of config instead.

tests/adapters/mqtt/test_environment.py::test_a_broker_that_refuses_us_is_a_connection_error_naming_the_refusal
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/test_environment.py:34: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/adapters/mqtt/test_environment.py: 1 warning
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/conftest.py:70: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/adapters/mqtt/test_environment.py::test_a_broker_that_leaves_fails_the_act_and_nothing_is_sent_when_it_is_back
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/test_environment.py:65: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/kernel/test_an_adapter_is_built_once_per_type.py::test_a_type_never_seen_is_built_once_and_then_never_again
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/pydantic/type_adapter.py:677: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Defaulting to left to right union serialization - failed to get discriminator value for tagged union serialization [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Started` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Composed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Invoked` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `EffectRecorded` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Observed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Proposed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Refused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ApprovalRequested` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `InputRequested` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Spawned` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanAdmitted` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanRefused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Held` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `UsageReported` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Reasoning` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ModeChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `WorkspaceChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Ended` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    return self.serializer.to_json(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=== 2254 passed, 8 skipped, 24 deselected, 85 warnings in 216.82s (0:03:36) ====
```

### Merged-tree 0.47.1: lint, format, mypy and pytest — exit 0

Commands: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`,
`uv run pytest`, with the disposable PostgreSQL URLs configured.

```text
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/amqtt/contexts.py:192: DeprecationWarning: sys_interval is deprecated, use 'plugins' to define configuration
    warnings.warn("sys_interval is deprecated, use 'plugins' to define configuration",

tests/adapters/mqtt/test_environment.py: 3 warnings
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/amqtt/contexts.py:196: DeprecationWarning: 'auth' and 'topic-check' are deprecated, use 'plugins' to define configuration
    warnings.warn("'auth' and 'topic-check' are deprecated, use 'plugins' to define configuration",

tests/adapters/mqtt/test_environment.py: 3 warnings
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/conftest.py:41: DeprecationWarning: Loading plugins from EntryPoints is deprecated and will be removed in a future version. Use `plugins` section of config instead.

tests/adapters/mqtt/test_environment.py::test_a_broker_that_refuses_us_is_a_connection_error_naming_the_refusal
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/test_environment.py:34: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/adapters/mqtt/test_environment.py: 1 warning
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/conftest.py:70: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/adapters/mqtt/test_environment.py::test_a_broker_that_leaves_fails_the_act_and_nothing_is_sent_when_it_is_back
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/test_environment.py:65: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/kernel/test_an_adapter_is_built_once_per_type.py::test_a_type_never_seen_is_built_once_and_then_never_again
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/pydantic/type_adapter.py:677: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Defaulting to left to right union serialization - failed to get discriminator value for tagged union serialization [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Started` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Composed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Invoked` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `EffectRecorded` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Observed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Proposed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Refused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ApprovalRequested` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `InputRequested` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Spawned` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanAdmitted` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanRefused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Held` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `UsageReported` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Reasoning` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ModeChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `WorkspaceChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Ended` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    return self.serializer.to_json(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=== 2260 passed, 8 skipped, 24 deselected, 85 warnings in 210.57s (0:03:30) ====
```

### Merged-tree 0.47.2: lint, format, mypy and pytest — exit 0

Commands: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`,
`uv run pytest`, with the disposable PostgreSQL URLs configured.

```text
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/amqtt/contexts.py:192: DeprecationWarning: sys_interval is deprecated, use 'plugins' to define configuration
    warnings.warn("sys_interval is deprecated, use 'plugins' to define configuration",

tests/adapters/mqtt/test_environment.py: 3 warnings
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/amqtt/contexts.py:196: DeprecationWarning: 'auth' and 'topic-check' are deprecated, use 'plugins' to define configuration
    warnings.warn("'auth' and 'topic-check' are deprecated, use 'plugins' to define configuration",

tests/adapters/mqtt/test_environment.py: 3 warnings
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/conftest.py:41: DeprecationWarning: Loading plugins from EntryPoints is deprecated and will be removed in a future version. Use `plugins` section of config instead.

tests/adapters/mqtt/test_environment.py::test_a_broker_that_refuses_us_is_a_connection_error_naming_the_refusal
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/test_environment.py:34: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/adapters/mqtt/test_environment.py: 1 warning
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/conftest.py:70: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/adapters/mqtt/test_environment.py::test_a_broker_that_leaves_fails_the_act_and_nothing_is_sent_when_it_is_back
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/test_environment.py:65: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/kernel/test_an_adapter_is_built_once_per_type.py::test_a_type_never_seen_is_built_once_and_then_never_again
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/pydantic/type_adapter.py:677: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Defaulting to left to right union serialization - failed to get discriminator value for tagged union serialization [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Started` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Composed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Invoked` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `EffectRecorded` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Observed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Proposed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Refused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ApprovalRequested` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `InputRequested` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Spawned` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanAdmitted` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanRefused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Held` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `UsageReported` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Reasoning` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ModeChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `WorkspaceChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Ended` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    return self.serializer.to_json(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=== 2264 passed, 8 skipped, 24 deselected, 85 warnings in 198.34s (0:03:18) ====
```

### Merged-tree 0.47.3: lint, format, mypy and pytest — exit 0

Commands: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`,
`uv run pytest`, with the disposable PostgreSQL URLs configured.

```text
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/amqtt/contexts.py:192: DeprecationWarning: sys_interval is deprecated, use 'plugins' to define configuration
    warnings.warn("sys_interval is deprecated, use 'plugins' to define configuration",

tests/adapters/mqtt/test_environment.py: 3 warnings
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/amqtt/contexts.py:196: DeprecationWarning: 'auth' and 'topic-check' are deprecated, use 'plugins' to define configuration
    warnings.warn("'auth' and 'topic-check' are deprecated, use 'plugins' to define configuration",

tests/adapters/mqtt/test_environment.py: 3 warnings
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/conftest.py:41: DeprecationWarning: Loading plugins from EntryPoints is deprecated and will be removed in a future version. Use `plugins` section of config instead.

tests/adapters/mqtt/test_environment.py::test_a_broker_that_refuses_us_is_a_connection_error_naming_the_refusal
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/test_environment.py:34: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/adapters/mqtt/test_environment.py: 1 warning
tests/adapters/mqtt/test_mqtt.py: 12 warnings
tests/adapters/mqtt/test_review_findings.py: 6 warnings
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/conftest.py:70: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/adapters/mqtt/test_environment.py::test_a_broker_that_leaves_fails_the_act_and_nothing_is_sent_when_it_is_back
  /Users/avinash/Workspace/Projects/shadow-hdk/tests/adapters/mqtt/test_environment.py:65: DeprecationWarning: `BrokerSysPlugin`: `psutil` will be removed as a project-level dependency in future versions. Please explicitly update your environment to use the optional dependency to ensure compatibility: 'amqtt[dollarsys]'

tests/kernel/test_an_adapter_is_built_once_per_type.py::test_a_type_never_seen_is_built_once_and_then_never_again
  /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk/.venv/lib/python3.14/site-packages/pydantic/type_adapter.py:677: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Defaulting to left to right union serialization - failed to get discriminator value for tagged union serialization [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Started` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Composed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Invoked` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `EffectRecorded` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Observed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Proposed` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Refused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ApprovalRequested` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `InputRequested` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Spawned` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanAdmitted` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanRefused` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Held` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `UsageReported` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Reasoning` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ModeChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `WorkspaceChanged` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Ended` - serialized value may not be as expected [input_value=Completed(output='ok', kind='completed'), input_type=Completed])
    return self.serializer.to_json(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=== 2274 passed, 8 skipped, 24 deselected, 85 warnings in 210.51s (0:03:30) ====
```

## Closure gate — exit 0

All 182 tracked package files match the release tag in both wheel and sdist for every
version, including provider TOML records and skill data. All 42 file hashes still match PyPI.
The final tracking tree passed lint, format, strict types and the full suite with disposable
PostgreSQL: 2,274 passed, 8 skipped, 24 live cases deselected, 85 warnings.
Raw output: `evidence/release-train-closure-gate.txt`.
