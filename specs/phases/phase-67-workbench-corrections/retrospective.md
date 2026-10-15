# Phase 67 retrospective — release candidate

Implementation acceptance passes on the phase branch. Protected landing, exact-head CI,
publication and fresh index installations remain pending; latest published is 0.47.3.

The owner expanded a maintenance phase to optional browser/workbench primitives. Engines stay
behind ports: direct Playwright, pinned isolated mitmproxy, psutil and defusedxml. Core contracts
only add generic images, ownership and private SDK bootstrap. Products choose packs and policy.

Real controls rejected redirect routing and plain CONNECT as adequate origin enforcement.
The adopted gateway checks decrypted schemes before upstream connection; tests observe real
TCP and UDP contacts with positive controls. Repeated cancellation and teardown failure exposed
store-hold, UTF-8 and descendant cleanup defects, recorded as BUG-241/242/243.

SDK catalogue capture is more informative than accepting flags: Codex project skill discovery
survived native-tool switches. A private launch directory closes that repository bootstrap path.
The real SDK calls MCP and resumes using a deterministic local model, without account traffic.
Older TypeScript hosts needed explicit resource negotiation, rather than guessing error codes.

Frozen large-repository budgets pass. Installed-wheel controls run outside the source tree on
Python 3.12; the base wheel contains neither optional engines nor a browser binary. A separate
pinned CPython source smoke restores an external edit without touching HEAD or the user index.
The first full run's only failures were old release-number expectations, corrected for 0.48.0.

## Verification Evidence

> **Superseded for 0.48.0 by _Acceptance re-run — 2026-10-15_ at the end of this file.** The run
> recorded immediately below predates the element-handle work, the replacement candidate's
> retirement and the catalogue bound controls, so it does not accept the current tree. It is kept
> because it is what the owner stop checkpoint was taken against.

SHADOW_HDK_TEST_CODEX=1 SHADOW_HDK_BROWSER_TESTS=1 SHADOW_HDK_BROWSER_INSTALL_TESTS=1 PLAYWRIGHT_BROWSERS_PATH=/tmp/hdk67-browser-binaries uv run --all-extras pytest -q — exit 0

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
    PydanticSerializationUnexpectedValue(Defaulting to left to right union serialization - failed to get discriminator value for tagged union serialization [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Started` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Composed` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Invoked` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `EffectRecorded` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Observed` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Proposed` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Refused` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ApprovalRequested` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `InputRequested` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Spawned` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanAdmitted` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `PlanRefused` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Held` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `UsageReported` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Reasoning` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `ModeChanged` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `WorkspaceChanged` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    PydanticSerializationUnexpectedValue(Expected `Ended` - serialized value may not be as expected [input_value=Completed(output='ok', ki...='completed', images=()), input_type=Completed])
    return self.serializer.to_json(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2357 passed, 29 skipped, 25 deselected, 85 warnings in 278.38s (0:04:38)
```

uv run ruff check — exit 0

```text
All checks passed!
```

uv run ruff format --check — exit 0

```text
586 files already formatted
```

uv run --all-extras mypy — exit 0

```text
Success: no issues found in 552 source files
```

uv run --all-extras pytest -m benchmark -q -s — exit 0

```text
{'fixture': 'workbench-v1', 'files': 100000, 'ignored_files': 100000, 'platform': 'macOS-27.0.1-arm64-arm-64bit-Mach-O', 'python': '3.14.6', 'git': 'git version 2.54.0 (Apple Git-157)', 'seconds': {'glob': 0.5668, 'grep': 0.5368, 'snapshot_cold': 0.6322, 'snapshot_unchanged': 0.6259, 'snapshot_one_edit': 0.6019, 'restore': 0.6753}}
.
  100 sequential steps: 76.4 ms (0.764 ms/step, best of 9), 203 events
.
  50-way fan-out: 32.3 ms (best of 9), 103 events
..
  100 steps in 10 nested subgraphs: 80.4 ms (0.804 ms/step, best of 9), 203 events
.
5 passed, 2406 deselected in 32.50s
```

installed wheel: Python 3.12 pytest controls outside the checkout — exit 0

```text
installed package: /tmp/hdk67-release-extras/lib/python3.12/site-packages/shadow_hdk/__init__.py
....................................s.................................   [100%]
=============================== warnings summary ===============================
tests/adapters/browser/test_real_browser.py:22
  /private/tmp/hdk67-installed-controls/tests/adapters/browser/test_real_browser.py:22: PytestUnknownMarkWarning: Unknown pytest.mark.browser - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    pytestmark = [pytest.mark.anyio, pytest.mark.browser, pytest.mark.timeout(180)]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
69 passed, 1 skipped, 1 warning in 36.25s
```

installed base wheel: Python 3.12 optional-engine smoke — exit 0

```text
{"version": "0.48.0", "base_has_no_optional_engines": true, "browser_declarations": 17, "gateway_resource_packaged": true, "missing_extras_explicit": true}
```

## Remaining release gate

Exact-head CI includes Python 3.12–3.14 with PostgreSQL, both Linux confinement mechanisms,
real browser on Linux/macOS, actual Codex SDK on Linux/macOS and all helper wheels. Future landing/publication would require renewed owner authorization: the current instruction
prohibits merge, tag and publish. This checklist is pending, not an instruction to execute it.

## Owner stop checkpoint — supersedes acceptance claims above
The 2,357-pass local suite, 552-file types, benchmarks and 69-pass installed wheel controls above
predate the launch-catalogue and agent-browser implementation. Those artifacts are stale and
must be rebuilt; they do not establish acceptance of the checkpoint being committed now.

Latest focused evidence preserved in `evidence/`:
- `g6-agent-reference-controls.txt`: 2 real reference/image/lifecycle controls pass.
- `g6-selected-real-controls.txt`: exit 1, 15 passed / 3 failed in 159.35s; agent-browser fails
  HTTP error navigation (`ERR_HTTP_RESPONSE_CODE_FAILURE`) and two waits using
  `#done:text-is('Finished')`. These are incomplete behavior/compatibility controls; the waits
  fail before their final network assertions, so do not claim candidate network denial passed.
- `browser-engine-comparison/`: pinned raw local results and scripts, including explicit local
  Browse with 35 references. ADR records licenses, decision and limitations.
- `g8-recognized-model-controls.txt`: 3 actual Codex SDK controls pass, including resumed turns.
- `g8-catalogue-green.txt`: 29 focused controls pass; `g8-catalogue-restored.txt`: 8 pass.
- `g8-pre-agent-types.txt`: 553 files pass before the new agent adapter; no exact-checkpoint
  full lint/format/types gate is claimed. New agent/catalogue mutation proof remains pending.

Known test sessions completed (browser exit 1, local Browse exit 0). Process inventory shows no
owned active test/mutation/browser/gateway runner. Mutation runners use saved bytes in `finally`
and earlier restored controls remain recorded; no active mutation needed restoration at stop.
All remaining source changes are preserved as legitimate candidate WIP, not reverted to HEAD.
Goal paused by owner. No new implementation, release gate, merge, tag or publish is run.

## Acceptance re-run — 2026-10-15

Supersedes the evidence above and the stop checkpoint below for the current tree. Every command
was re-run from this checkout after the element handles landed, the replacement candidate was
retired and the catalogue bound controls were added.

SHADOW_HDK_TEST_CODEX=1 SHADOW_HDK_BROWSER_TESTS=1 SHADOW_HDK_BROWSER_INSTALL_TESTS=1 PLAYWRIGHT_BROWSERS_PATH=/tmp/hdk67-browser-binaries uv run --all-extras pytest -q — exit 0

```text
2375 passed, 29 skipped, 25 deselected, 85 warnings in 303.85s (0:05:03)
```

uv run ruff check — exit 0 · uv run ruff format --check — exit 0 · uv run mypy — exit 0

```text
All checks passed!
536 files already formatted
Success: no issues found in 555 source files
```

uv run pytest -m benchmark -q -s — exit 0

```text
{'fixture': 'workbench-v1', 'files': 100000, 'ignored_files': 100000, 'seconds': {'glob': 0.5292, 'grep': 0.517, 'snapshot_cold': 0.6387, 'snapshot_unchanged': 0.5754, 'snapshot_one_edit': 0.5877, 'restore': 0.6906}}
  100 sequential steps: 76.9 ms (0.769 ms/step, best of 9), 203 events
  50-way fan-out: 30.6 ms (best of 9), 103 events
  100 steps in 10 nested subgraphs: 77.6 ms (0.776 ms/step, best of 9), 203 events
5 passed, 2424 deselected in 30.40s
```

schema and TypeScript client: generation produced no diff, so the committed contracts match this
source; `tsc --noEmit` and the build both exit 0.

```text
wrote 29 contracts under clients/typescript/src/schemas and clients/typescript/src/schemas.ts
git status --short clients/typescript/ — empty
npm run check — exit 0
npm run build — exit 0
```

wheel and sdist built at 0.48.0; version lockstep consistent across the distribution, the Linux
helper pin and the helper crate. Asserted against the built artifact rather than the tree: the
retired engine, its native client, asset resolution and download step are absent, and the handle
implementation is present.

```text
Successfully built dist/shadow_hdk-0.48.0.tar.gz
Successfully built dist/shadow_hdk-0.48.0-py3-none-any.whl
retired files in the wheel: none
handle markers in the wheel's engine: 3
browser pack files shipped: 7 (was 11)
```

installed wheel: Python 3.12 controls outside the checkout — exit 0

```text
installed package: /tmp/hdk480-venv/lib/python3.12/site-packages/shadow_hdk/__init__.py
installed version: 0.48.0
retired engine import: ImportError (correct)
handles_in('- button "Save" [ref=e5]') -> {'@e5': {'role': 'button', 'name': 'Save'}}
137 passed in 95.60s (0:01:35)
```

Two exclusions from that selection, stated rather than silent. `tests/test_versions.py` inspects
repository files (`native/sandbox/Cargo.toml`) that no installed package carries, so it is a
checkout control and not an installed one. `test_real_codex_governance.py` is excluded under
TD-023: it passes from a checkout and fails from a copied tree, and the mechanism is unexplained,
so it is recorded as unexplained rather than benign. CI runs it from a checkout, where it passes.
A first attempt at these controls also failed nine browser cases because the fresh environment's
engine resolves a different Chromium build than the isolated path held; the refusal was correct
behaviour from `install_browser=False`, and the build was installed rather than the check relaxed.

installed base wheel: Python 3.12 optional-engine smoke — exit 0

```text
playwright installed: False
Failed -> Install shadow-hdk[browser] to use the optional browser component.
```
