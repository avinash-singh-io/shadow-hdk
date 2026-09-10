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
from shadow_hdk.kernel.observations import Failed, Observation
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.runtime.leash import run_leashed

WORKSPACE = ScopeSet.of("workspace")
EVERYTHING = ScopeSet(everything=True)
"""What an uncontained subprocess can really touch."""

#: What a child process is allowed to inherit. Everything else — tokens, keys, proxies — is dropped,
#: because a script the model wrote should not be handed the operator's credentials by accident.


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
        """What running code here really does — **all** of it (BUG-018).

        A plain subprocess honours `cwd` and nothing else. `cd ..` works, an absolute path works,
        and the whole filesystem is one command away; it can open a socket whatever we pass it.
        Only a deployment that *proves* isolation (D25, D36) may claim otherwise, and then it is
        containment making the claim true rather than the adapter asserting it.

        This got `reaches` right from the start and its own docstring said why — *a governance
        system fed a lie is worse than one fed nothing* — while `reads` and `writes` stayed pinned
        to the workspace whatever `contained` said. So a mode permitting workspace writes was in
        fact permitting writes anywhere, and the record said the workspace. The rule was written
        down and applied to one field of three.

        The consequence is deliberate and should be felt: on an ordinary host, letting an agent run
        code **is** letting it reach the machine, and a policy now has to say so out loud instead of
        being told a comfortable thing.
        """
        loose = not self._contained
        return EffectProfile(
            reads=EVERYTHING if loose else WORKSPACE,
            writes=EVERYTHING if loose else WORKSPACE,
            reaches=self._network or loose,
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
        # The leash lives in the runtime since Phase 11, so a second sandbox can share it without
        # this package and that one importing each other.
        return await run_leashed(
            argv, cwd=self._root, timeout_s=self._timeout_s, output_limit=self._output_limit
        )

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
