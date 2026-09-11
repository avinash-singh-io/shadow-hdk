"""Talk to it.

    uv run python -m examples.coder [workspace]

Everything it does happens in the workspace directory and nowhere else, and every action it takes
is printed as it lands on the run's event stream — so you can watch the governing happen rather
than take it on trust.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from examples.coder.session import NoProvider, a_conversation
from shadow_hdk.kernel import Ended, Event, Invoked, Observed, Reasoned, Refused, Spent

DIM, BOLD, OFF = "\033[2m", "\033[1m", "\033[0m"


_conversation: list[str] = []


def show(event: Event) -> None:
    """What the run did, as it does it. This is the whole demonstration.

    Only the conversation's own `Ended` is shown. Every tool the provider calls is a **child run**
    with an `Ended` of its own, and printing all of them says "run ended" after each file write,
    which reads as something finishing when nothing has.
    """
    if not _conversation:
        _conversation.append(event.run_id)
    if isinstance(event, Reasoned):
        # What it thought, before what it did (D45) — the line a person most wants to read.
        thought = event.text.strip().replace("\n", " ")
        print(f"\033[36m  ∴ {thought[:200]}{OFF}", flush=True)
    elif isinstance(event, Invoked) and event.step != "converse":
        print(f"{DIM}  · {event.component}{OFF}", flush=True)
    elif isinstance(event, Observed) and event.step != "converse":
        print(f"{DIM}    → {str(event.observation)[:150]}{OFF}", flush=True)
    elif isinstance(event, Refused):
        print(f"\033[31m  ✕ refused: {event.reason}{OFF}", flush=True)
    elif isinstance(event, Spent):
        print(f"{DIM}    ({event.usage}){OFF}", flush=True)
    elif isinstance(event, Ended) and event.run_id == _conversation[0]:
        print(f"{DIM}  [conversation ended: {event.reason}]{OFF}", flush=True)


async def main() -> int:
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    confined = "--confined" in sys.argv
    root = Path(argv[0] if argv else "./coder-workspace").resolve()
    try:
        async with a_conversation(root, confined=confined, on_event=show) as talk:
            print(f"{BOLD}Workspace:{OFF} {root}")
            print(f"{DIM}Its own tools are refused; the only ones it has are this run's.{OFF}")
            if confined:
                print(
                    f"{DIM}Mode {BOLD}confined{OFF}{DIM}: files only. Ask it to run something and "
                    f"watch the policy refuse.{OFF}"
                )
            else:
                # Said plainly, every time. A demonstration that quietly granted the machine and
                # called it a workspace would be the exact failure BUG-018 was.
                print(
                    f"\033[33mMode {BOLD}building{OFF}\033[33m: running code is permitted, and on "
                    f"an ordinary host that reaches this whole machine — not just the workspace. "
                    f"Pass --confined to refuse it.{OFF}"
                )
            print(f"{DIM}Ctrl-D or 'exit' to finish.{OFF}\n")
            while True:
                try:
                    said = input(f"{BOLD}you ›{OFF} ").strip()
                except EOFError:
                    print()
                    return 0
                if said in ("exit", "quit"):
                    return 0
                if not said:
                    continue
                done = await talk.turn(said)
                print(f"\n{BOLD}agent ›{OFF} {done.text}\n")
                if done.failed:
                    print(f"\033[31m  (the provider reported this turn as failed){OFF}\n")
    except NoProvider as nothing:
        print(f"{nothing}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
