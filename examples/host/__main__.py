"""Run a brief through the host.

    uv run python -m examples.host "brief" [--brain=script|key|subscription] [--root=DIR]
                                          [--mode=workspace-write|full|read-only] [--yes]

`--yes` answers every question the policy raises with Allow; without it the person is asked at the
terminal. A run left unanswered is parked in the store — `<root>.runs.sqlite`, **beside** the
workspace and never inside it, because a store the agent can write to is not the host's — and its
id is printed.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from examples.host.brains import NoBrain, by_key, by_subscription, scripted
from examples.host.host import host
from shadow_hdk.kernel import Allow, Refuse
from shadow_hdk.kernel.ports import Judgement
from shadow_hdk.runtime.environment import CannotEnforce, Mode

BOLD, DIM, OFF = "\033[1m", "\033[2m", "\033[0m"


def flag(name: str, default: str) -> str:
    for arg in sys.argv[1:]:
        if arg.startswith(f"--{name}="):
            return arg.split("=", 1)[1]
    return default


def at_the_terminal(question: str) -> Judgement | None:
    print(f"\n\033[33m? {question}{OFF}")
    said = input(f"{BOLD}allow? [y/N/park]{OFF} ").strip().lower()
    if said in ("y", "yes"):
        return Allow()
    if said in ("park", "p"):
        return None
    return Refuse("the host said no")


async def main() -> int:
    words = [a for a in sys.argv[1:] if not a.startswith("--")]
    brief = " ".join(words) or "Look around the workspace and write down what you find."
    root = Path(flag("root", "./host-workspace")).resolve()
    mode: Mode = flag("mode", "workspace-write")  # type: ignore[assignment]
    which = flag("brain", "script")
    try:
        if which == "key":
            brain = by_key(brief)
        elif which == "subscription":
            brain = await by_subscription(brief, workspace=root)
        else:
            brain = scripted(brief)
        print(f"{BOLD}Brain:{OFF} {brain.called}   {BOLD}Mode:{OFF} {mode}")
        print(f"{BOLD}Workspace:{OFF} {root}")
        network = "allowed, because this brain is a service" if brain.reaches else "refused"
        print(
            f"{DIM}Policy: reads anywhere, writes in the workspace, a write outside is asked, "
            f"network {network}.{OFF}\n"
        )
        answer = (lambda _q: Allow()) if "--yes" in sys.argv else at_the_terminal
        outcome = await host(
            brief,
            root=root,
            brain=brain,
            store=root.with_name(root.name + ".runs.sqlite"),
            mode=mode,
            answer=answer,
        )
    except NoBrain as nothing:
        print(f"{nothing}", file=sys.stderr)
        return 2
    except CannotEnforce as cannot:
        print(f"\033[31m{cannot}{OFF}", file=sys.stderr)
        return 3
    print()
    if outcome.question:
        print(f"{DIM}parked on: {outcome.question}\nrun id: {outcome.run_id}{OFF}")
        return 4
    print(f"{DIM}[run {outcome.run_id} ended: {outcome.ended}]{OFF}")
    print(f"{BOLD}Ledger:{OFF}\n{outcome.ledger.as_json()}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
