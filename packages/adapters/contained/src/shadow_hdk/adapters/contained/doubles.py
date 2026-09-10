"""A backend that can be told whether it actually contains anything, for tests of the contract."""

from __future__ import annotations

import sys


class FakeIsolation:
    """Records what it wrapped, and either denies the capability test or does not.

    A double cannot pretend its way past D36 — the sandbox runs the check and reads the outcome —
    so a fake that *contains* has to genuinely stop the probe. It does that by replacing the
    probe's argv with a program that reports being denied, which is what a real box's kernel would
    make the probe discover for itself. Everything else passes straight through to the host, which
    is what a fake box is.
    """

    name = "fake"
    binary = "fake-runtime"

    def __init__(
        self,
        *,
        contains: bool = True,
        present: bool = True,
        declares: str | None = None,
        probe_runs: bool = True,
    ) -> None:
        self._contains = contains
        self._present = present
        self._declares = declares
        self._probe_runs = probe_runs
        self.wrapped: list[list[str]] = []

    def present(self) -> bool:
        return self._present

    def declares(self) -> str | None:
        return self._declares

    def wrap(self, argv: list[str]) -> list[str]:
        self.wrapped.append(list(argv))
        if not self._is_the_probe(argv):
            # A fake box is no box: real work runs on the host, and only the tests know that.
            return list(argv)
        if not self._probe_runs:
            # A backend that cannot run the check at all — the inconclusive case, which must not
            # be mistaken for a denial.
            return ["sh", "-c", "exit 3"]
        if self._contains:
            return ["sh", "-c", "echo DENIED"]
        return list(argv)

    @staticmethod
    def _is_the_probe(argv: list[str]) -> bool:
        return len(argv) == 3 and argv[0] == sys.executable and "connect_ex" in argv[2]


__all__ = ["FakeIsolation"]
