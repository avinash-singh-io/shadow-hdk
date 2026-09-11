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
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.jsonl.paths import read_at, texts_at
from shadow_hdk.kernel import Dialect, Provider, ToolSource, Turn, Usage
from shadow_hdk.runtime import current_run

DEFAULT_TIMEOUT_S = 600.0


def _cents(dollars: Any) -> int | None:
    """Dollars as a provider reports them, cents as the kernel counts them.

    **Rounded up.** A tenth of a cent is not nothing, and a purse that floored every small turn to
    zero would let a long conversation cost real money while reporting none of it.
    """
    if not isinstance(dollars, int | float):
        return None
    return int(math.ceil(float(dollars) * 100))


class JsonlSession:
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
    ) -> None:
        self._provider = provider
        self._dialect = provider.dialect or Dialect()
        self._binary = binary
        self._env = dict(env)
        self._workspace = workspace
        self._tools = tools
        self._timeout_s = timeout_s
        self._process: asyncio.subprocess.Process | None = None
        self._session_id: str | None = None
        self.stderr: str = ""

    # ------------------------------------------------------------------ the process

    def _argv(self) -> list[str]:
        argv = [str(self._binary), *self._provider.launch_args]
        dialect = self._dialect
        if self._session_id and dialect.resume_args:
            argv += [*dialect.resume_args, self._session_id]
        return argv

    async def _start(self) -> asyncio.subprocess.Process:
        return await asyncio.create_subprocess_exec(
            *self._argv(),
            cwd=str(self._workspace) if self._workspace else None,
            env=self._env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # Its own group, so closing the session ends the tree it started (D35). A coding CLI
            # spawns compilers, language servers and test runners.
            start_new_session=True,
        )

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
            self._process = None
        return turn

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
            if kind in dialect.think_on:
                # **Why before what** (D45). The tool calls this thinking led to are already
                # landing on the record through the socket as they happen; a thought held back
                # until the turn ended would read as hindsight. So each one goes on the record as
                # it arrives — when there is a run to put it on — and the whole comes back on the
                # turn for a caller holding that instead.
                for thought in texts_at(event, dialect.think_at):
                    thought_so_far.append(thought)
                    if (context := current_run()) is not None:
                        await context.reasoned(thought)
            if kind in dialect.say_on:
                said += texts_at(event, dialect.say_at)
            if dialect.session_id_at and (found := read_at(event, dialect.session_id_at)):
                self._session_id = str(found)
            if kind in dialect.done_on:
                return self._finished(event, said, thought_so_far)
        # The stream ended without the event that says a turn ended: the child died, or it does not
        # announce completion. What it said is still what it said.
        return Turn(
            text="".join(said), failed=bool(said) is False, reasoning="".join(thought_so_far)
        )

    def _finished(self, event: Any, said: list[str], thought: list[str]) -> Turn:
        dialect = self._dialect
        final = read_at(event, dialect.done_at)
        return Turn(
            text=final if isinstance(final, str) else "".join(said),
            reasoning="".join(thought),
            stop_reason=str(read_at(event, dialect.stop_reason_at) or ""),
            failed=bool(read_at(event, dialect.failed_at)),
            usage=Usage(
                input_tokens=_as_int(read_at(event, dialect.input_tokens_at)),
                output_tokens=_as_int(read_at(event, dialect.output_tokens_at)),
                cost_cents=_cents(read_at(event, dialect.cost_usd_at)),
            ),
        )

    async def close(self) -> None:
        """Ending the session ends the tree it started (D35)."""
        process, self._process = self._process, None
        if process is None or process.returncode is not None:
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


def _as_int(value: Any) -> int | None:
    return int(value) if isinstance(value, int) else None


__all__ = ["JsonlSession"]
