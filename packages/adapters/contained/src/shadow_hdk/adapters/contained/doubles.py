"""A backend that can be told to pass or fail its proof, for tests of the contract."""

from __future__ import annotations

from shadow_hdk.adapters.contained.sandbox import Proof


class FakeIsolation:
    """Records what it wrapped and how often it was probed, and proves what it is told to."""

    name = "fake"
    binary = "fake-runtime"

    def __init__(self, *, proves: bool = True, present: bool = True) -> None:
        self._proves = proves
        self._present = present
        self.wrapped: list[list[str]] = []
        self.probes = 0

    def present(self) -> bool:
        return self._present

    def probe(self) -> Proof | None:
        self.probes += 1
        if not self._proves:
            return None
        return Proof(backend=self.name, observed="the fake kernel announced itself", at="t")

    def wrap(self, argv: list[str]) -> list[str]:
        self.wrapped.append(list(argv))
        # A fake box is no box: the argv runs on the host, and only the tests know that.
        return list(argv)


__all__ = ["FakeIsolation"]
