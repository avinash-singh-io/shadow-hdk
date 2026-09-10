"""Run code with a leash, and say plainly that a leash is what it is.

`09` §5's third form of "program" is code in a sandbox — *a component with `contained: true`,
present only on deployments that have a sandbox, absent everywhere else.* This adapter is the
cheapest such component and the least capable one, and both facts are in its effect profile rather
than in a comment.

**`contained` has no default.** A deployment states it. There is no safe value to guess, because a
sandbox that claimed containment it did not have would be the most dangerous lie this system could
tell: everything downstream — what a mode permits, what the model is even shown — is computed from
that one boolean.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import JsonValue

from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import EffectProfile, ScopeSet
from shadow_hdk.kernel.observations import Completed, Failed, Observation
from shadow_hdk.kernel.ports import ComponentPort

WORKSPACE = ScopeSet.of("workspace")

#: What a child process is allowed to inherit. Everything else — tokens, keys, proxies — is dropped,
#: because a script the model wrote should not be handed the operator's credentials by accident.
KEPT_ENV = ("PATH", "LANG", "LC_ALL", "TMPDIR", "HOME")


class SubprocessSandbox(ComponentPort):
    def __init__(
        self,
        root: Path,
        *,
        contained: bool,
        timeout_s: float = 30.0,
        output_limit: int = 64_000,
        network: bool = False,
        at: str = "",
        source: str = "sandbox",
    ) -> None:
        self._root = Path(root).resolve()
        self._contained = contained
        self._timeout_s = timeout_s
        self._output_limit = output_limit
        self._network = network
        self._at = at
        self._source = source

    @property
    def effects(self) -> EffectProfile:
        """What running code here really does.

        `reaches` is `network or not contained` rather than plain `network`. A plain subprocess on
        an ordinary host can open a socket whatever we pass it, so only a deployment asserting real
        isolation gets to claim a run does not reach outside. A governance system fed a lie is worse
        than one fed nothing.
        """
        return EffectProfile(
            reads=WORKSPACE,
            writes=WORKSPACE,
            reaches=self._network or not self._contained,
            reversible=False,
            contained=self._contained,
            costs=False,
        )

    # ------------------------------------------------------------------ the port

    async def registrations(self) -> Sequence[Registration]:
        return [
            self._registration(
                "run_python",
                "Run a Python script in the workspace and return what it printed.",
                {"source": {"type": "string", "description": "The script to run."}},
                ["source"],
            ),
            self._registration(
                "run_shell",
                "Run a shell command in the workspace and return what it printed.",
                {"command": {"type": "string", "description": "The command to run."}},
                ["command"],
            ),
        ]

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        arguments = inputs if isinstance(inputs, dict) else {}
        match registration:
            case "run_python":
                source = arguments.get("source")
                if not isinstance(source, str):
                    return Failed("run_python needs `source`, a string")
                return await self._run([sys.executable, "-c", source])
            case "run_shell":
                command = arguments.get("command")
                if not isinstance(command, str):
                    return Failed("run_shell needs `command`, a string")
                return await self._run(["/bin/sh", "-c", command])
        return Failed(f"no component registered as {registration!r}")

    # ------------------------------------------------------------------ the leash

    async def _run(self, argv: list[str]) -> Observation:
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=self._root,
                env={name: os.environ[name] for name in KEPT_ENV if name in os.environ},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as broken:
            return Failed(f"{type(broken).__name__}: {broken}")
        try:
            out, err = await asyncio.wait_for(process.communicate(), self._timeout_s)
        except TimeoutError:
            process.kill()
            await process.wait()
            return Failed(f"timed out after {self._timeout_s:g}s")

        stdout, cut_out = self._cap(out)
        stderr, cut_err = self._cap(err)
        return Completed(
            {
                "exit_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
                # Said, not silent: an agent reasoning from half an answer while believing it whole
                # is a worse failure than one told it only got half.
                "truncated": cut_out or cut_err,
            }
        )

    def _cap(self, raw: bytes) -> tuple[str, bool]:
        text = raw.decode("utf-8", errors="replace")
        if len(text) <= self._output_limit:
            return text, False
        return text[: self._output_limit], True

    def _registration(
        self, name: str, description: str, properties: dict[str, JsonValue], required: list[str]
    ) -> Registration:
        return Registration(
            id=name,
            component=Component(
                interface=Interface(
                    name=name,
                    description=description,
                    input_schema={
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                ),
                effects=self.effects,
                provenance=Provenance(
                    registered_by=self._source, adapter="sandbox-subprocess", at=self._at
                ),
                labels=frozenset({"tool", "program"}),
            ),
        )


__all__ = ["SubprocessSandbox"]
