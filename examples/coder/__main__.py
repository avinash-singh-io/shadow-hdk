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
from shadow_hdk.kernel import Ended, Event, Invoked, Observed, Refused, Spent

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
    if isinstance(event, Invoked) and event.step != "converse":
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
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "./coder-workspace").resolve()
    try:
        async with a_conversation(root, on_event=show) as talk:
            print(f"{BOLD}Workspace:{OFF} {root}")
            print(f"{DIM}Its own tools are refused; the only ones it has are this run's.{OFF}")
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
