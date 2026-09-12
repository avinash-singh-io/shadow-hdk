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

from shadow_hdk.kernel import (
    Ended,
    Event,
    Invoked,
    Observed,
    Reasoning,
    RefusedEvent,
    UsageReported,
)
from shadow_hdk.providers import NoProvider
from shadow_hdk.runtime import Approvals
from shadow_hdk.runtime.environment import CannotEnforce
from shadow_hdk.runtime.environment import Mode as EnvironmentMode
from shadow_hdk.serve import Harness

DIM, BOLD, OFF = "\033[2m", "\033[1m", "\033[0m"


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

    A turn's own `Ended` says only "completed" and is not shown; every tool the provider calls is a
    **child run** under the turn with an `Ended` of its own, and printing those said "run ended"
    after each file write, which reads as something finishing when nothing has.
    """

    if isinstance(event, Reasoning):
        # What it thought, before what it did (D45) — the line a person most wants to read.
        thought = event.text.strip().replace("\n", " ")
        print(f"\033[36m  ∴ {thought[:200]}{OFF}", flush=True)
    elif isinstance(event, Invoked) and not event.step.startswith("turn-"):
        print(f"{DIM}  · {event.component}{OFF}", flush=True)
    elif isinstance(event, Observed) and not event.step.startswith("turn-"):
        print(f"{DIM}    → {str(event.observation)[:150]}{OFF}", flush=True)
    elif isinstance(event, RefusedEvent):
        # The *event*, not the observation of the same name — the first cut checked the
        # observation and no refusal was ever shown.
        print(f"\033[31m  ✕ refused: {event.reason}{OFF}", flush=True)
    elif isinstance(event, UsageReported):
        print(f"{DIM}    ({event.usage}){OFF}", flush=True)
    elif isinstance(event, Ended) and event.reason != "completed":
        print(f"{DIM}  [the turn ended: {event.reason}]{OFF}", flush=True)


async def answer_questions(questions: Approvals) -> None:
    """The person's side of D58: a tool call the policy asks about waits here for a `y`/`n`.

    The provider is blocked on that call, so the question is put to the terminal as it arrives;
    `input()` is blocking and the run is on this loop, so it runs in a thread.
    """
    from shadow_hdk.runtime import Approve, Deny

    while True:
        pending = await questions.next()
        about = f" · {pending.component} {pending.inputs}" if pending.component else ""
        print(f"\n\033[33m? {pending.question}{about}{OFF}", flush=True)
        said = await asyncio.to_thread(input, f"{BOLD}approve? [y/N]{OFF} ")
        questions.answer(
            pending.handle,
            Approve() if said.strip().lower() in ("y", "yes") else Deny("the person said no"),
        )


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
    answering: asyncio.Task[None] | None = None
    try:
        # The facade (D71): the shipped composition behind three lines. Everything underneath —
        # the thread, the handles — is reachable when this REPL wants it, and it wants one: the
        # approvals handle, to answer the policy's questions at the terminal.
        async with Harness(root, mode=mode, provider=want) as h:
            thread = h.thread
            answering = asyncio.create_task(answer_questions(h.approvals))
            print(f"{BOLD}Workspace:{OFF} {root}  {DIM}({thread.record.provider}){OFF}")
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
                async for part in h.turn(said):
                    if part.event is not None:
                        show(part.event)
                turn = thread.record.turns[-1]
                print(f"\n{BOLD}agent ›{OFF} {turn.text}\n")
                if turn.outcome != "completed":
                    print(f"\033[31m  (the turn ended {turn.outcome}){OFF}\n")
    except NoProvider as nothing:
        print(f"{nothing}", file=sys.stderr)
        return 2
    except CannotEnforce as cannot:
        # The environment refused to exist rather than quietly widen (D48). The right thing for a
        # person to see, verbatim: it names what is missing and what to pass instead.
        print(f"\033[31m{cannot}{OFF}", file=sys.stderr)
        return 3
    finally:
        if answering is not None:
            answering.cancel()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
