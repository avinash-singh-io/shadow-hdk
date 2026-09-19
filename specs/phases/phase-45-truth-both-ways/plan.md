---
type: Plan
status: in-progress
---

# Phase 45 — truth both ways — Plan

```
# Sequential:  Group 1 → Group 2 → Group 3 → Group 4 → Group 5
# Each group opens RED — its tests written and watched failing for their stated reasons — then
# goes green; no task is marked done without that recorded (Rule 13, strict).
```

The four-zero gate (`ruff check`, `ruff format --check`, `mypy`, `pytest -m 'not live'`) runs per
group on 3.12; the final gate on 3.12 and 3.14. Where a provider file is changed, the change is
proven twice: on a recorded stream (the suite) and live (`-m live`, this machine's signed-in Claude
Code 2.1.278 and Codex 0.154.0), with the measurement's lines in the history.

## Reference specs

`specs/architecture/adapters.md` (the agent adapter: a provider is a file, D40; the modes
adapter: deny → ceiling → ask → mode → allow, D85), `runtime.md` (the thread, the meter D84/D90,
the judgement's context D82), `wire.md` (the thread crossed; error kinds D92), `testing.md`.
`docs/for-a-product.md` §2, §8, §9 are the consumer-facing statements this phase changes.
The admission rule and the owner's standing rule (the kit is a substrate) govern every row.

## The measured facts this plan rests on

- Claude Code 2.1.278, `--resume <unknown>`, 2026-09-20: one stderr line `No conversation found
  with session ID: <id>`; one JSON line `{"type":"result","subtype":"error_during_execution",
  "is_error":true,…,"errors":["No conversation found with session ID: <id>"],"usage":{
  "input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,
  "output_tokens":0,…}}`; exit 0.
- Codex 0.154.0, `exec resume <unknown> --json`, 2026-09-20: nothing on stdout; stderr
  `Error: thread/resume: thread/resume failed: no rollout found for thread id <id> (code -32600)`.
- Codex's `turn.completed` usage (measured 2026-09-11, in `codex.toml`): `input_tokens`,
  `cached_input_tokens`, `cache_write_input_tokens`, `output_tokens`, `reasoning_output_tokens`.
- Codex's flags: `-m/--model <MODEL>`; effort is a config override, `-c model_reasoning_effort="<v>"`.
- LangChain's `UsageMetadata.input_token_details` carries `cache_read` and `cache_creation`.
- The JSONL session opens the CLI with `stderr=PIPE` and never reads it (BUG-059): a CLI that
  writes more than the pipe holds blocks; and Codex's *session gone* is on that pipe.

## Group 1 — What a turn really cost (ENH-023, D141)

- RED (tests/adapters/jsonl/test_cache_tokens_are_read.py, tests/adapters/langchain/…,
  tests/runtime/test_the_meter_counts_cache_tokens.py, tests/kernel/…): a Codex-shaped stream
  with the measured usage → `Turn.usage.cache_read_tokens == 26112`, `cache_write_tokens == 0`; a
  Claude-shaped result with `cache_read_input_tokens`/`cache_creation_input_tokens` → the same
  fields; a stream without them → `None`; a LangChain message with `input_token_details` →
  the fields, without → `None`; the meter sums cache tokens across turns and `Spent` carries
  `cache_read_tokens`/`cache_write_tokens`; a checkpoint's `spent` restores them; a record
  written before this phase (no keys) loads with zeros; `Usage`/`Spent` round-trip the contracts.
- `kernel/usage.py`: the two fields. `kernel/threads.py::Spent`: the two counters.
  `kernel/providers.py::Dialect`: `cache_read_tokens_at`, `cache_write_tokens_at`.
  `adapters/jsonl/session.py::_finished` reads them; `adapters/langchain/model.py::_usage_of`
  reads `input_token_details`; `runtime/session.py::LeaseMeter` counts, `spent()`/`restore()`
  carry them; `runtime/conversation.py`/`threads.py` where `Spent` is built from the meter;
  `codex.toml`, `claude-code.toml` (with the measured lines in their comments); the contracts
  regenerated (`schemas/`), the TypeScript types regenerated, `docs/packages/*` where `Spent` is
  shown.
- Verify: the group's tests green; `uv run pytest tests/kernel tests/runtime tests/adapters/jsonl
  tests/adapters/langchain tests/wire tests/invariants -q`; `npm run generate && npm run check`
  without drift; the mutation (cache fields not counted) fails the meter test.

**Commit:** `feat(usage): cache read and write tokens, unknown never zero (ENH-023, D141)`

## Group 2 — Why a turn really failed (ENH-024, D139; BUG-059)

- RED (tests/adapters/jsonl/test_a_session_gone_is_said.py, tests/runtime/test_a_turn_names_
  why_it_failed.py, tests/wire/test_session_gone_crosses_the_wire.py, the parity invariant):
  a fake CLI printing the measured Claude Code lines → `Turn.failed and Turn.session_gone`; a
  fake CLI printing Codex's stderr line and nothing on stdout → the same; a fake CLI failing with
  another text → `failed`, not `session_gone`; a fake CLI writing 1 MB to stderr → the turn still
  ends (BUG-059); `Thread.resume(...)` then `turn()` on a provider double saying gone → the turn
  record `failed` with `failure == "session_gone"` and `SessionGone(thread_id, session_id,
  provider)` raised at the end of the stream; over the wire `turn/start` answers
  `error.data.kind == "session_gone"` with both ids; `ERROR_KINDS` gains the kind and the TS
  client's union with it.
- `kernel/ports.py::Turn.session_gone`; `kernel/providers.py::Dialect.session_gone_matches`
  (loaded as a tuple, like `deltas`); `claude-code.toml`: `failed_text_at = "errors"`,
  `session_gone_matches = ["No conversation found with session ID"]`; `codex.toml`:
  `session_gone_matches = ["no rollout found for thread id"]`; `adapters/jsonl/session.py`: a
  stderr reader task started with the process, the last 64 KB kept on `self.stderr`, joined lists
  in `_finished`'s failure text, `session_gone` decided from text and stderr against the matches
  — on the done event and on the stream ending without one; `kernel/threads.py::TurnRecord.failure`;
  `runtime/conversation.py`: the turn component carries `session_gone` out (`Failed` with a
  typed marker the conversation reads), the turn record written with `failure`;
  `runtime/threads.py::SessionGone` raised after the stream; `wire/peer.py::error_data`,
  `wire/protocol.py::ERROR_KINDS`, `wire/threads.py::_turn_json` carries `failure`; the TS client.
- Verify: the group's tests green; tests/adapters/jsonl tests/runtime tests/wire tests/serve
  tests/invariants; mutations — matches ignored → 2 fail; `failure` not written → 1 fails.

**Commit:** `feat(threads): a turn's failure is typed — session_gone on the record, raised, on the wire (ENH-024, D139; BUG-059)`

## Group 3 — A host's words per turn; a second CLI's behaviour (ENH-037, D140; ENH-028)

- RED (tests/runtime/test_a_turns_words_are_the_turns.py, tests/wire/…,
  `tests/adapters/jsonl/test_a_behaviour_becomes_flags.py` extended,
  `tests/providers/test_library.py`): a governance double recording contexts → the turn given
  `attributes={"workspace": "w1"}` is judged with it and the next turn without; a rule scoped
  `attribute:workspace=w1` allows in that turn and asks in the next; a reserved name refused;
  `resume(attributes=)` replaces the record's words and `record.attributes` says so; on the
  wire `turn/start {attributes}` and `thread/resume {attributes}`; `Behaviour(model="gpt-5",
  effort="low")` on the shipped Codex file → argv holds `-m gpt-5` and
  `-c model_reasoning_effort="low"`; `unmapped_behaviour` on Codex names only `system`,
  `append_system`, `temperature`; a `behaviour_args` entry with `template` but no `{value}` is
  malformed.
- `kernel/providers.py::BehaviourArg.template` (`""` = the value as is); `adapters/jsonl/
  transport.py::argv_for` renders it; `providers/library.py` loads it; `codex.toml` maps `model`
  (`-m`) and `effort` (`-c`, `model_reasoning_effort="{value}"`); `runtime/conversation.py`:
  `turn(attributes=)` held for the turn and merged last in `context_for`; `runtime/threads.py`:
  `turn(attributes=)` through, `resume(attributes=)` replacing and saving; `wire/threads.py`
  reads both; the TS client's `thread.turn`/`resume` options.
- Verify: green; mutations — the turn's words leaking into the next turn → 1 fails; the template
  not rendered → 1 fails.

**Commit:** `feat(threads): a turn's words are the turn's; Codex's model and effort as data (ENH-037, D140; ENH-028)`

## Group 4 — The ceiling stands (ENH-038, D138); the matrix; the invariant (ENH-032)

- RED (tests/adapters/modes/test_a_reach_from_the_process_is_an_egress_channel.py,
  tests/invariants/test_a_provider_is_a_file.py, the CI matrix by inspection): under shipped
  `read-only` an effect `reaches=True, contained=False, writes=∅` is refused; under
  `workspace-write` refused; under a product mode file with ceiling `contained = false` and
  `ask_above.contained = true` it is asked and a contained reach allowed; the `ddgs` battery's
  file unchanged (`contained = false`); the invariant walks `src/shadow_hdk/kernel` and
  `src/shadow_hdk/runtime` code tokens (docstrings and comments stripped by `tokenize`) and
  refuses `claude`, `codex`, `openai`, `anthropic`, `ollama`, `opencode`; its self-test plants
  one and sees it caught.
- `adapters/modes/registry.py::_looking` ceiling `contained=True`; `docs/packages/adapters-
  modes.md` (or the modes guide that exists): *opening web reads with a mode of your own*;
  `.github/workflows/ci.yml` `check` over `python-version: ["3.12", "3.13", "3.14"]`;
  `.python-version` → `3.14`; `pyproject.toml` classifiers `3.14`; the invariant.
- Verify: green; the invariant's mutation; CI green on the three legs for the pushed commit.

**Commit:** `feat(modes): a reach from the serving process is an egress channel — read-only's ceiling says contained (ENH-038, D138); the 3.12–3.14 matrix (ENH-032); a provider is a file, by a test`

## Group 5 — The live proofs, the docs, the release *(last)*

- Live, this machine: `uv run pytest -m live tests/test_a_cli_plans_through_the_socket.py -rs`
  with Claude Code selected (Phase 36's owed half); one Codex turn with
  `Behaviour(model=…, effort="low")` whose argv and stream are recorded (ENH-028 measured); one
  Claude Code and one Codex turn whose `Spent` carries cache tokens (ENH-023 measured). Each
  measurement's lines into `history.md` as `[NOTE]`; a provider that is not signed in skips and
  says so — recorded as such, never as passed.
- Docs: the 0.34 note under `docs/migrations/`; `docs/for-a-product.md` — the two ports and one surface
  (§ the served runtime), §8 session resume rewritten around `session_gone`, §9 cache tokens,
  §2 Codex's mapped fields, a paragraph on per-turn words; `docs/packages/adapters-langchain.md`
  — the endpoints table and the local desktop; `docs/packages/wire.md` — the kind and the
  parameters; the TS README.
- Backlog: ENH-023, ENH-024, ENH-028, ENH-032, ENH-037, ENH-038 closed; BUG-059 filed and
  closed; `specs/decisions/index.md` D138–D141 rows. Version 0.34.0, `EXPECTED`, `uv lock`,
  changelog, status row; `[ARCH_CHANGE]` entries for `/sync-docs`.
- Verify: the four-zero gate on 3.12 and 3.14; `npm run generate && npm run check && npm run
  build`; `momentum okf check .`; the wheel fresh; CI green; `/complete-phase` → STOP at the gate.

**Commits:** `docs: 0.34 — truth both ways` · `chore(release): 0.34.0`
