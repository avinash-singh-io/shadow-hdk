---
type: Ad-hoc Record
---

# Ad-hoc Work Record: 2026-09-13-one-distribution

> **Type**: quick-task — the owner's call before the first PyPI publish
> **Created**: 2026-09-13
> **Branch**: chore/one-distribution
> **Backlog**: BUG-036, BUG-037 filed and closed here
> **Status**: shipped as v0.27.0

## Current Behavior

Eighteen distributions — `shadow-hdk`, `shadow-hdk-kernel`, `-wire`, `-providers`, `-serve`
and thirteen `-adapters-<name>` — from eighteen `packages/*/pyproject.toml`, each carrying a slice
of one PEP 420 namespace `shadow_hdk` under its own `src/`. A workspace install stitched them; a
consumer would have had to know which of eighteen names to ask for, and the publish workflow
would have claimed eighteen names on PyPI. Under that layout mypy, asked for every package,
discovered **253 of 371** files: a namespace split across eighteen source roots is not a package
it walks, and the gate invariant asserted the configuration rather than the walk.

## Expected Behavior

**One distribution, `shadow-hdk`, with extras (D78).** `pip install shadow-hdk` installs the
kit — kernel, runtime, wire, providers, serve, and the adapters that need nothing beyond the base
dependencies; `shadow-hdk[langchain]`, `[openai]`, `[anthropic]`, `[ollama]`, `[huggingface]`,
`[mqtt]`, `[otel]`, `[sandbox]`, `[search]` add the SDK a specialised adapter needs; `[all]` is
every extra, so the whole kit installs with one line. One `src/shadow_hdk` package tree, one
`pyproject.toml`, one version, one `py.typed`; the eighteen package READMEs become
`docs/packages/`. D9 amended: *one version* was the rule; *one distribution* is now the fact.

## What was found by doing it

- **Sixty-three latent strict-mypy errors in twenty-six files** the old net never reached — every
  one fixed at its cause, not silenced (a stale ignore removed; a `Protocol` where a structural
  type was meant; `replace()` instead of `**{}` splats; a name reused for two things renamed).
  Among them **BUG-036**: `LocalEnvironment`'s OpenSandbox path built `Volume(host=str)` where the
  SDK wants `Host(path=…)`, `mountPath`, `readOnly` and `NetworkPolicy(defaultAction=…)` — a
  runtime `ValidationError` on the first sandbox open, verified against the SDK.
- **`RemoteModel.stream` returned a coroutine around an iterator**, so `async for` over the wire's
  model raised. The four remote halves implemented the ports structurally, and the invariant
  that holds every implementation to a contract finds classes by their bases — BUG-007's shape
  one layer over. They name their ports now; a contract module runs all four over a loopback; the
  suites gained `using()` for a port with a lifetime.
- **BUG-037**: the registry's one funnel took the *last* port to offer an id. Found the moment
  `ddgs` became installable in the dev venv (`--all-extras`): two batteries offered `web_search`,
  the second answered with the wrong shape, and nothing said why. The first port to offer an id
  keeps it — a registration the run started with cannot be taken over by a port that came later —
  and the hidden offer is named in `shadowed`, beside `unreachable` and `refused` (TD-006's door on
  `RunContext`). A closed Python battery now offers nothing, as a stopped MCP server does
  (`CallableComponents.remove`, the mirror of `add`).
- **The sdist was 11 MB**: 2,273 of its files were the TypeScript client's `node_modules` — a
  nested `.gitignore` the sdist builder did not honour. What the sdist holds is declared
  (`only-include`), and an invariant looks inside it: 284 kB.
- **The README's first code block** showed an `EffectProfile` with fields the kernel does not
  have (`frozenset` scopes, a `reaches` set, a `Cost`). Fixed to the kernel's shape, and the two
  self-contained blocks now run as printed under a test.

## Unchanged Behavior

No wire method, schema or port signature changes; every import path `shadow_hdk.<part>` is what
it was; `harness.toml`, the CLI and the console scripts are unchanged; a workspace member that
pinned `shadow-hdk` still resolves — to the whole kit.

## Verification Evidence

Captured fresh 2026-09-13 on the branch:

- `uv run ruff check -q` → 0 · `uv run ruff format --check -q` → 0 · `uv run mypy` → 0 (**377**
  files; 253 under the old layout)
- `uv run pytest -q -p no:cacheprovider -m 'not live'` → **1436 passed, 2 skipped, 12 deselected**
- `tests/invariants/test_the_gate_covers_every_package.py` asks mypy's own discovery and holds it
  to the files on disk — a planted `src/orphan/stray.py` → RED (*mypy never sees these 1 files*)
- `tests/invariants/test_a_wheel_carries_what_it_needs.py`: a base install needs no extra (AST walk
  of every third-party import against `dependencies`), every extra covers its part, `[all]` is
  everything — a planted `import paho.mqtt.client` in the kernel → RED
- RED first for BUG-037 (five tests: last-wins seen as `'ddgs' == 'reference'`); mutations —
  the guard dropped → 5 fail; `shadowed` never recorded → 3 fail; the stream chunk not `done` →
  1 fail; a Python battery's close forgetting nothing → 1 fail; `only-include` dropped → the sdist
  invariant names 2,535 stray files; a wrong README block → RED
- `uv build` → one wheel (355 kB) and one sdist (284 kB); `twine check` PASSED on both
- a clean venv with nothing but `shadow_hdk-0.27.0-py3-none-any.whl[all]`: `import shadow_hdk`,
  `.serve`, `.adapters.langchain`, `.adapters.mqtt`, `.adapters.otel`, `.adapters.environment`,
  `.serve.web` — no source path on `sys.path`; `__version__` 0.27.0; transports `acp`, `jsonl`;
  `shadow-hdk` prints its usage; `shadow-hdk serve harness.toml --stdio` answers `initialize`
  with `{"protocol_version": "1"}`; the README's bare run prints `started … invoked say-hello …
  ended`; `detect()` finds Claude Code, Codex CLI and OpenCode
- `~/Workspace/Projects/shadow-hdk-demo` depends on `shadow-hdk[all]` from the sibling checkout;
  `uv sync` → `shadow-hdk 0.27.0` editable, `ddgs 9.16.0`

## History

### [DECISION] 2026-09-13 — D78: one distribution, `shadow-hdk`, with extras

One PyPI project, `shadow-hdk`; the parts stay parts (the AST invariants hold kernel, runtime,
wire, providers, serve and each adapter to their layering) but ship as one wheel. The base
dependencies are what the kit needs to run as a harness (`pydantic`, `langgraph`, `mcp`,
`anyio`, `agent-client-protocol`, `starlette`, `uvicorn`, `httpx`); every SDK a specialised
adapter needs is an extra named for the adapter or the model vendor; `[all]` is every extra, so
the whole kit installs with one line. *Why:* eighteen names on an index are eighteen things to
version, publish, document and pin for a kit that is one thing to its consumer; the owner's call
(*"one package with extras — and if someone wants the full package, they still should be able
to"*). *Amends* D9: one version was the rule, one distribution is the fact; a contract change is
still a minor bump and a Pins row. *Overturned by:* a part with a consumer of its own that
cannot carry the base dependencies — the kernel alone, say — which would be a second distribution
with a reason, not a return to eighteen.
