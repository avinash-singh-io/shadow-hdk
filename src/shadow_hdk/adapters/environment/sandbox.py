"""An environment inside a box somebody else built (D50)."""

from __future__ import annotations

from pathlib import Path

from shadow_hdk.adapters.environment.backends import Box, IsolationBackend, prove_box
from shadow_hdk.kernel.capabilities import EnvironmentRequirements
from shadow_hdk.kernel.observations import Observation
from shadow_hdk.kernel.workspace import Workspace
from shadow_hdk.runtime.environment import (
    CannotEnforce,
    Environment,
    Isolation,
    Mode,
    requires,
)


class SandboxEnvironment(Environment):
    """The same five operations, the same one derivation, the same proof — in a box."""

    def __init__(
        self,
        root: Path,
        *,
        mode: Mode,
        box: Box,
        isolation: object,
        timeout_s: float = 60.0,
        output_limit: int = 64_000,
        at: str = "",
        requirements: EnvironmentRequirements | None = None,
    ) -> None:
        assert isinstance(isolation, Isolation)
        super().__init__(
            root,
            mode=mode,
            isolation=isolation,
            source="sandbox",
            at=at,
            requirements=requirements,
        )
        self._box = box
        self._timeout_s = timeout_s
        self._output_limit = output_limit

    @classmethod
    async def open(
        cls,
        backend: IsolationBackend,
        root: Path | None = None,
        *,
        mode: Mode = "workspace-write",
        timeout_s: float = 60.0,
        output_limit: int = 64_000,
        at: str = "",
        requirements: EnvironmentRequirements | None = None,
    ) -> SandboxEnvironment:
        """Open a box, prove it, and refuse a mode it cannot make true — closing the box on the
        way out, because a refused environment must not leave a sandbox running."""
        if (why := backend.present()) is not None:
            raise CannotEnforce(f"{backend.name} is not reachable: {why}")
        where = (root or Path.cwd()).resolve()
        box = await backend.open(where, mode)
        try:
            isolation = await prove_box(box, mode=mode, mechanism=backend.name)
            requires(isolation, mode)
        except BaseException:
            await box.close()
            raise
        return cls(
            where,
            mode=mode,
            box=box,
            isolation=isolation,
            timeout_s=timeout_s,
            output_limit=output_limit,
            at=at,
            requirements=requirements,
        )

    def _prove_now(self, workspace: Workspace, mode: Mode) -> Isolation:
        """A box mounts one root at `MOUNT` and was proven when it opened; it cannot take a
        second root or another mode without another box. Refused honestly (D76): the isolation
        it has is offered only for the workspace and mode it was proven for."""
        if workspace.roots != self.workspace.roots or mode != self.mode:
            raise CannotEnforce(
                "a box is proven for one root and one mode; open another box for a different "
                "workspace or mode"
            )
        return self.isolation

    async def _read(self, path: str) -> str:
        return await self._box.read(path)

    async def _write(self, path: str, content: str) -> int:
        return await self._box.write(path, content)

    async def _delete(self, path: str) -> None:
        await self._box.delete(path)

    async def _list(self, path: str) -> list[str]:
        return await self._box.list(path)

    async def _run(self, argv: list[str]) -> Observation:
        return await self._box.run(argv, timeout_s=self._timeout_s, output_limit=self._output_limit)

    async def close(self) -> None:
        await self._box.close()


__all__ = ["SandboxEnvironment"]
