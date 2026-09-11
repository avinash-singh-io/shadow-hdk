"""A host with a page: the conversation, the agent's steps as they happen, its acts in the sandbox
and on files, and a button when the policy asks.

    uv run python -m examples.studio [workspace] [--provider=claude-code|codex|opencode]
                                     [--mode=workspace-write|full|read-only] [--port=8765]

Then open http://127.0.0.1:8765. Everything on the page is the run's own record: the events the
runtime emits, folded into steps (D46) the same way any client would fold them, the `Reasoned`
lines ahead of the acts they led to (D45), the environment's answers as they land, and the
policy's questions answered live while the provider waits (D58). Nothing here is drawn from
anything but the stream — the page is a reader of the record, which is the point of having one.

It binds to loopback only. It is an example, not a product: no accounts, one conversation.
"""
