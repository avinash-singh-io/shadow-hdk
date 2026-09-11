"""The coder example's REPL closes the provider however the person leaves (BUG-019).

No provider is driven here — this is the example's own exit path, worth nothing on the subscription.
"""

from __future__ import annotations

import pytest


def test_ctrl_c_leaves_the_repl_the_way_ctrl_d_does(monkeypatch: pytest.MonkeyPatch) -> None:
    """A person leaving with Ctrl-C must reach the same `return 0` as Ctrl-D, so the `async with`
    holding the provider open closes it on the record — the ordinary path for BUG-019, with the
    runtime's exit finaliser (D53) as the backstop, not the plan."""
    import builtins

    from examples.coder.__main__ import ask

    def interrupted(_prompt: str) -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", interrupted)
    assert ask("you › ") is None

    monkeypatch.setattr(builtins, "input", lambda _p: "  hello  ")
    assert ask("you › ") == "hello"
