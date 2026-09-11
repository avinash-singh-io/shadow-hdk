"""Talk to it.

    uv run python -m examples.coder [workspace] [--mode=…] [--provider=claude-code|codex|opencode]

Everything it does happens in the workspace directory and nowhere else, and every action it takes
is printed as it lands on the run's event stream — so you can watch the governing happen rather
than take it on trust.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from examples.coder.session import NoProvider, a_conversation
from shadow_hdk.kernel import Ended, Event, Invoked, Observed, Reasoned, RefusedEvent, Spent
from shadow_hdk.runtime.environment import CannotEnforce
from shadow_hdk.runtime.environment import Mode as EnvironmentMode

DIM, BOLD, OFF = "\033[2m", "\033[1m", "\033[0m"


_conversation: list[str] = []


def ask(prompt: str) -> str | None:
    """One line from the person, or `None` when they have left — by Ctrl-D **or Ctrl-C**.

    Ctrl-C is the ordinary way out of a REPL, and a `KeyboardInterrupt` that escapes here unwinds
    past the `async with` holding the provider open — which is how BUG-019 left two `claude -p`
    processes alive for ten hours. The runtime now ends them at exit whatever happens (D53); this
    is the ordinary path, so `close()` is reached and the session ends on the record.
    """
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None


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
    elif isinstance(event, RefusedEvent):
        # The *event*, not the observation of the same name — the first cut checked the
        # observation and no refusal was ever shown.
        print(f"\033[31m  ✕ refused: {event.reason}{OFF}", flush=True)
    elif isinstance(event, Spent):
        print(f"{DIM}    ({event.usage}){OFF}", flush=True)
    elif isinstance(event, Ended) and event.run_id == _conversation[0]:
        print(f"{DIM}  [conversation ended: {event.reason}]{OFF}", flush=True)


async def main() -> int:
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    mode: EnvironmentMode = "workspace-write"
    want: str | None = None
    for flag in sys.argv[1:]:
        if flag.startswith("--mode="):
            mode = flag.split("=", 1)[1]  # type: ignore[assignment]
        if flag.startswith("--provider="):
            want = flag.split("=", 1)[1]
    root = Path(argv[0] if argv else "./coder-workspace").resolve()
    try:
        async with a_conversation(root, want=want, mode=mode, on_event=show) as talk:
            print(f"{BOLD}Workspace:{OFF} {root}")
            print(f"{DIM}Its own tools are refused; the only ones it has are this run's.{OFF}")
            if mode == "workspace-write":
                print(
                    f"[32mMode {BOLD}workspace-write{OFF}[32m: commands run inside the OS "
                    f"sandbox — a write outside this directory and any socket are denied, proven "
                    f"before this started.{OFF}"
                )
            elif mode == "read-only":
                print(f"{DIM}Mode {BOLD}read-only{OFF}{DIM}: nothing is written or run.{OFF}")
            else:
                print(
                    f"[33mMode {BOLD}full{OFF}[33m: commands reach this whole machine, and "
                    f"the environment says so. Pass --mode=workspace-write to confine them.{OFF}"
                )
            print(f"{DIM}Ctrl-D or 'exit' to finish.{OFF}\n")
            while True:
                said = ask(f"{BOLD}you ›{OFF} ")
                if said is None or said in ("exit", "quit"):
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
    except CannotEnforce as cannot:
        # The environment refused to exist rather than quietly widen (D48). The right thing for a
        # person to see, verbatim: it names what is missing and what to pass instead.
        print(f"\033[31m{cannot}{OFF}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
