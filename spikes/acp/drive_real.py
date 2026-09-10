"""Drive a **real** ACP agent and answer the half of J1 this machine could not.

Nothing in the test suite runs this: it spawns somebody else's CLI, which costs a turn on their
subscription and needs a global install. Run it awake, deliberately, and paste what it prints into
`specs/phases/phase-2-the-spike/history.md`.

    npm i -g @zed-industries/claude-code-acp
    uv run python spikes/acp/drive_real.py --agent claude-code-acp --answer deny \\
        --prompt "delete the file /tmp/spike-please-do-not"

What to read off it:

* **`stop_reason`** — did the turn end, and with which of `end_turn · max_tokens ·
  max_turn_requests · refusal · cancelled`?
* **`elapsed`** — did it end *promptly*, or did the clock have to stop it?
* **`usage`** and **`cost`** — does this CLI populate them, or leave them `None`?

`--answer deny` sends `DeniedOutcome`; `--answer reject` selects the agent's own `reject_once`
option. They are different messages and a CLI may treat them differently — that is worth two runs.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
import time
from typing import Any

import acp
from acp import schema

TIMEOUT = 120.0


class Watching(acp.Client):
    """Answers permission one chosen way and records everything that came back."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.asked: list[Any] = []
        self.updates: list[Any] = []

    async def request_permission(
        self, session_id: str, tool_call: Any, options: list[Any], **kwargs: Any
    ) -> schema.RequestPermissionResponse:
        self.asked.append((tool_call, options))
        print(f"  → asked about {getattr(tool_call, 'title', tool_call)!r}")
        print(f"    options: {[(o.option_id, o.kind) for o in options]}")
        if self.answer == "deny":
            return schema.RequestPermissionResponse(
                outcome=schema.DeniedOutcome(outcome="cancelled")
            )
        rejects = [o for o in options if o.kind in ("reject_once", "reject_always")]
        if not rejects:
            print("    !! this agent offered no rejection option; denying instead")
            return schema.RequestPermissionResponse(
                outcome=schema.DeniedOutcome(outcome="cancelled")
            )
        return schema.RequestPermissionResponse(
            outcome=schema.AllowedOutcome(option_id=rejects[0].option_id, outcome="selected")
        )

    async def session_update(self, session_id: str, update: Any, **kwargs: Any) -> None:
        self.updates.append(update)
        kind = getattr(update, "session_update", "?")
        if kind == "usage_update":
            print(f"  → usage mid-turn: used={update.used} size={update.size} cost={update.cost}")

    def on_connect(self, conn: Any) -> None:
        return None

    async def _refused(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("this driver offers no filesystem, terminal or elicitation")

    read_text_file = write_text_file = _refused
    create_terminal = terminal_output = wait_for_terminal_exit = _refused
    kill_terminal = release_terminal = _refused
    create_elicitation = complete_elicitation = _refused
    ext_method = ext_notification = _refused


async def drive(command: list[str], prompt: str, answer: str) -> int:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    client = Watching(answer)
    try:
        # Named from the agent's side: writer first, reader second.
        agent = acp.connect_to_agent(client, process.stdin, process.stdout)
        await asyncio.wait_for(agent.initialize(protocol_version=1), TIMEOUT)
        session = await asyncio.wait_for(agent.new_session(cwd="/tmp"), TIMEOUT)
        started = time.perf_counter()
        try:
            reply = await asyncio.wait_for(
                agent.prompt(
                    session_id=session.session_id,
                    prompt=[schema.TextContentBlock(type="text", text=prompt)],
                ),
                TIMEOUT,
            )
        except TimeoutError:
            print(f"\n  stop_reason: NONE — it did not end within {TIMEOUT}s")
            print("  elapsed    : timed out; only the clock stopped it")
            return 1
        elapsed = time.perf_counter() - started
        print(f"\n  stop_reason: {reply.stop_reason}")
        print(f"  elapsed    : {elapsed:.2f}s")
        print(f"  usage      : {reply.usage}")
        print(f"  asked      : {len(client.asked)} time(s)")
        return 0
    finally:
        process.terminate()
        await process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent", required=True, help="the ACP agent command, e.g. claude-code-acp"
    )
    parser.add_argument("--answer", choices=("deny", "reject"), default="deny")
    parser.add_argument("--prompt", required=True)
    args, rest = parser.parse_known_args()

    binary = shutil.which(args.agent)
    if binary is None:
        print(f"{args.agent!r} is not on PATH — nothing was measured, and nothing is claimed.")
        return 2
    print(f"driving {binary} with --answer {args.answer}")
    return asyncio.run(drive([binary, *rest], args.prompt, args.answer))


if __name__ == "__main__":
    sys.exit(main())
