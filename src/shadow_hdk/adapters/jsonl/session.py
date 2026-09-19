"""Driving a CLI that answers in line-delimited JSON, by the dialect its provider file names.

One adapter for every CLI of this shape, because what differs between them is names and the names
are data (D40). Claude Code and Codex disagree about which key holds the event type, which type
carries assistant text, and what ends a turn; they agree that the answer arrives as JSON lines on a
pipe, which is the part worth writing once.

**No tool call comes back through here.** Under D42 the provider is launched with the run's own
registry as its tool source, so anything it does arrives as a step on our graph — judged on effects,
charged to the lease, on the event stream. What this reads out of the stream is what only the
provider knows: what it said, what it spent, and why it stopped.

**Everything is untrusted input.** A line nobody can parse is skipped, not fatal; a CLI printing a
banner or a progress bar on stdout is ordinary and must not lose the turn around it.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.jsonl.paths import read_at, texts_at
from shadow_hdk.kernel import AgentSession, Dialect, Provider, ToolSource, Turn, Usage
from shadow_hdk.runtime import current_run

DEFAULT_TIMEOUT_S = 600.0
STDERR_KEPT = 64 * 1024
"""How much of the CLI's stderr is kept: the tail, so the sentence that explains a failure is
there and a megabyte of progress bars is not."""


def _cents(dollars: Any) -> int | None:
    """Dollars as a provider reports them, cents as the kernel counts them.

    **Rounded up.** A tenth of a cent is not nothing, and a purse that floored every small turn to
    zero would let a long conversation cost real money while reporting none of it.
    """
    if not isinstance(dollars, int | float):
        return None
    return int(math.ceil(float(dollars) * 100))


class JsonlSession(AgentSession):
    """One CLI, held for as long as its dialect says to hold it.

    `resident` is a fact about the CLI: Claude Code with `--input-format stream-json` keeps reading
    stdin, so the conversation is one process and its own memory carries the history. `codex exec`
    is the other shape — a process per turn, threaded by the CLI's own resume flag.
    """

    def __init__(
        self,
        provider: Provider,
        *,
        binary: Path,
        env: Mapping[str, str],
        workspace: Path | None = None,
        tools: tuple[ToolSource, ...] = (),
        timeout_s: float = DEFAULT_TIMEOUT_S,
        resume: str | None = None,
        unmapped: tuple[str, ...] = (),
    ) -> None:
        self._provider = provider
        self._dialect = provider.dialect or Dialect()
        self._binary = binary
        self._env = dict(env)
        self._workspace = workspace
        self._tools = tools
        self._timeout_s = timeout_s
        self._process: asyncio.subprocess.Process | None = None
        self._session_id: str | None = resume or None
        """The CLI's own session id — read off its stream where the dialect says, or handed in
        to resume (D76): the first process is started with the dialect's resume flag, so a
        provider reopened after a mode change keeps its memory of the conversation."""
        self.stderr: str = ""
        """The tail of what the CLI wrote to stderr — the last `STDERR_KEPT` bytes — read as it
        arrives so a chatty CLI never blocks on a full pipe (BUG-059), and where Codex says a
        resumed session is gone (D139)."""
        self._stderr_reader: asyncio.Task[None] | None = None
        self._unmapped = unmapped

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def unmapped(self) -> tuple[str, ...]:
        """What the behaviour set that this record maps no flag for (ENH-020) — computed by the
        opener from the record's `behaviour_args`, carried here so the thread can say it."""
        return self._unmapped

    # ------------------------------------------------------------------ the process

    def _argv(self) -> list[str]:
        argv = [str(self._binary), *self._provider.launch_args]
        dialect = self._dialect
        if self._session_id and dialect.resume_args:
            argv += [*dialect.resume_args, self._session_id]
        return argv

    async def _start(self) -> asyncio.subprocess.Process:
        from shadow_hdk.runtime.processes import start_held

        # A session leader the runtime holds (D35, D53): closing the session ends the tree it
        # started — a coding CLI spawns compilers, language servers and test runners — and it
        # dies with this process, whatever ends it (BUG-019).
        process = await start_held(
            *self._argv(),
            cwd=str(self._workspace) if self._workspace else None,
            env=self._env,
            stdin=asyncio.subprocess.PIPE,
        )
        # **A pipe nobody reads is a deadlock waiting for a chatty CLI** (BUG-059): stderr is
        # drained as it arrives, its tail kept, whatever the CLI prints — a progress bar, a stack
        # of warnings, or the one line that says the session is gone.
        self.stderr = ""
        if process.stderr is not None:
            self._stderr_reader = asyncio.create_task(self._drain_stderr(process.stderr))
        return process

    async def _drain_stderr(self, stream: asyncio.StreamReader) -> None:
        while chunk := await stream.read(4096):
            self.stderr = (self.stderr + chunk.decode("utf-8", "replace"))[-STDERR_KEPT:]

    def _written(self, prompt: str) -> bytes:
        """How this CLI wants to be told. A fact about it, so it comes off the record."""
        if self._dialect.prompt_shape == "stream-json-user":
            return (
                json.dumps(
                    {
                        "type": "user",
                        "message": {"role": "user", "content": [{"type": "text", "text": prompt}]},
                    }
                )
                + "\n"
            ).encode()
        return (prompt + "\n").encode()

    # ------------------------------------------------------------------ a turn

    async def turn(self, prompt: str) -> Turn:
        if self._process is None or self._process.returncode is not None:
            self._process = await self._start()
        process = self._process
        assert process.stdin is not None and process.stdout is not None

        process.stdin.write(self._written(prompt))
        await process.stdin.drain()
        if not self._dialect.resident:
            process.stdin.close()

        try:
            async with asyncio.timeout(self._timeout_s):
                turn = await self._read_until_done(process)
        except TimeoutError:
            await self.close()
            return Turn(
                text=f"the provider did not finish within {self._timeout_s:g}s", failed=True
            )

        if not self._dialect.resident:
            await process.wait()
            await self._stderr_drained()
            self._process = None
        return turn

    async def _stderr_drained(self) -> None:
        """Wait for the reader to see the pipe close, so what the CLI wrote last is on
        `self.stderr` before anyone reads it."""
        reader, self._stderr_reader = self._stderr_reader, None
        if reader is not None:
            with contextlib.suppress(Exception):
                async with asyncio.timeout(2):
                    await reader

    async def _read_until_done(self, process: asyncio.subprocess.Process) -> Turn:
        assert process.stdout is not None
        said: list[str] = []
        thought_so_far: list[str] = []
        dialect = self._dialect
        while line := await process.stdout.readline():
            try:
                event = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                # A banner, a warning, a progress bar. Ordinary, and not this turn's business.
                continue
            if not isinstance(event, dict):
                continue
            kind = event.get(dialect.type_key)
            if matches(event, kind, dialect.think_on, dialect.subtype_key):
                # **Why before what** (D45). The tool calls this thinking led to are already
                # landing on the record through the socket as they happen; a thought held back
                # until the turn ended would read as hindsight. So each one goes on the record as
                # it arrives — when there is a run to put it on — and the whole comes back on the
                # turn for a caller holding that instead.
                for thought in texts_at(event, dialect.think_at):
                    # **Measured 2026-09-12 with `--include-partial-messages`:** Claude Code
                    # emits one `assistant` line per content block, each carrying the whole
                    # message so far, so the same thinking block arrived twice and went on the
                    # record twice. A thought is one thought.
                    if thought in thought_so_far:
                        continue
                    thought_so_far.append(thought)
                    if (context := current_run()) is not None:
                        await context.reasoning(thought)
            if dialect.deltas and matches(event, kind, dialect.delta_on, dialect.subtype_key):
                # **What is happening, beside the record** (D63). A streamed piece of thinking or
                # text is activity — the observer hears it as it arrives; nothing lands on the
                # record until the whole arrives, exactly as before.
                which = read_at(event, dialect.delta_kind_at)
                for delta in dialect.deltas:
                    if delta.on == which:
                        piece = read_at(event, delta.at)
                        if piece and (context := current_run()) is not None:
                            await context.activity(delta.kind, str(piece))
            if matches(event, kind, dialect.say_on, dialect.subtype_key):
                said += texts_at(event, dialect.say_at)
            if dialect.session_id_at and (found := read_at(event, dialect.session_id_at)):
                self._session_id = str(found)
            if matches(event, kind, dialect.done_on, dialect.subtype_key):
                return self._finished(event, said, thought_so_far)
        # The stream ended without the event that says a turn ended: the child died, or it does not
        # announce completion. What it said is still what it said — and when it said nothing, what
        # it wrote to stderr may be the reason (Codex says *no rollout found* there, D139).
        await self._stderr_drained()
        text = "".join(said)
        failed = not text
        if failed:
            # The last line it wrote to stderr is the nearest thing to a reason.
            text = (self.stderr.strip().splitlines() or [""])[-1]
        return Turn(
            text=text,
            failed=failed,
            reasoning="".join(thought_so_far),
            session_gone=failed and self._says_gone(text),
        )

    def _says_gone(self, text: str) -> bool:
        """Does the failure's text, or the CLI's stderr, say the resumed session is gone — by the
        file's own words (D139)? Nothing is inferred from an exit code or a shape."""
        matches = self._dialect.session_gone_matches
        return any(m in text or m in self.stderr for m in matches)

    def _finished(self, event: Any, said: list[str], thought: list[str]) -> Turn:
        dialect = self._dialect
        final = read_at(event, dialect.done_at)
        failed = bool(read_at(event, dialect.failed_at))
        text = final if isinstance(final, str) else "".join(said)
        if failed and not text:
            text = _sentence(read_at(event, dialect.failed_text_at))
        return Turn(
            text=text,
            reasoning="".join(thought),
            stop_reason=str(read_at(event, dialect.stop_reason_at) or ""),
            failed=failed,
            session_gone=failed and self._says_gone(text),
            usage=Usage(
                input_tokens=_as_int(read_at(event, dialect.input_tokens_at)),
                output_tokens=_as_int(read_at(event, dialect.output_tokens_at)),
                cost_cents=_cents(read_at(event, dialect.cost_usd_at)),
                cache_read_tokens=_as_int(read_at(event, dialect.cache_read_tokens_at)),
                cache_write_tokens=_as_int(read_at(event, dialect.cache_write_tokens_at)),
            ),
        )

    async def steer(self, text: str) -> bool:
        """A resident CLI reads its stdin between and during turns: another user message written
        while a turn runs is queued by the CLI and folded into the same turn (D63). A one-shot
        dialect has no open stdin to take it."""
        process = self._process
        if not self._dialect.resident or process is None or process.stdin is None:
            return False
        if process.returncode is not None or process.stdin.is_closing():
            return False
        process.stdin.write(self._written(text))
        await process.stdin.drain()
        return True

    async def interrupt(self) -> bool:
        """A dialect that names an interrupt line sends it; one that does not cannot be told, and
        the thread ends the turn by closing the session. Nothing is guessed."""
        process = self._process
        line = self._dialect.interrupt_line
        if not line or process is None or process.stdin is None or process.stdin.is_closing():
            return False
        process.stdin.write(line.encode() + b"\n")
        await process.stdin.drain()
        return True

    async def close(self) -> None:
        """Ending the session ends the tree it started (D35)."""
        process, self._process = self._process, None
        if process is None or process.returncode is not None:
            await self._stderr_drained()
            return
        if process.stdin is not None and not process.stdin.is_closing():
            process.stdin.close()
        try:
            async with asyncio.timeout(5):
                await process.wait()
        except TimeoutError:
            from shadow_hdk.runtime.processes import end_the_group

            end_the_group(process)
            await process.wait()


def matches(event: Any, kind: Any, entries: tuple[str, ...], subtype_key: str) -> bool:
    """Whether this line is one of `entries`: `type` alone, or `type/subtype` with the dialect's
    `subtype_key` read off the event. A `type/subtype` entry with no key to read matches nothing."""
    for entry in entries:
        if "/" in entry:
            wanted, sub = entry.split("/", 1)
            if kind == wanted and subtype_key and read_at(event, subtype_key) == sub:
                return True
        elif kind == entry:
            return True
    return False


def _as_int(value: Any) -> int | None:
    return int(value) if isinstance(value, int) else None


__all__ = ["JsonlSession"]


def _sentence(said: Any) -> str:
    """A failure's text as the dialect points at it: a string, or a list of them (Claude Code's
    `result.errors`) joined — never a dict rendered by accident."""
    if isinstance(said, str):
        return said
    if isinstance(said, list):
        return "\n".join(str(item) for item in said if isinstance(item, str | int | float))
    return ""
