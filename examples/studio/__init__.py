"""A host with a page: the conversation with the agent's trace **inline** — what it thought, what
it did and what came back, folded under each tool call in the order it happened; a question card
with Allow/Refuse where the policy asked, naming the tool and its arguments — and the environment
beside it: the root's files, the changed ones marked.

    uv run python -m examples.studio [workspace] [--provider=claude-code|codex|opencode]
                                     [--mode=workspace-write|full|read-only] [--port=8765]
                                     [--store=live.sqlite]

— which is `shadow-hdk serve --http --page examples/studio/page.html` with those flags, and
nothing of its own (D69): the page is served by `serve` itself and talks the wire — JSON-RPC over
`POST /rpc`, the runtime's replies and notifications down SSE from `GET /rpc` — with the same
methods the TypeScript client speaks. `thread/start` once at load (`thread/resume` when the
address names a thread; a reload resumes), `turn/start` per message, `approvals/answer`,
`thread/set_mode`, `modes/list`, `store/*` for the admin panel, `files/list` and `files/read` for
the environment pane.

Then open http://127.0.0.1:8765. Everything on the page is the run's own record: the events the
runtime emits, folded into items (D46) the same way any client would fold them, the `Reasoning`
lines ahead of the acts they led to (D45), the environment's answers as they land, and the
policy's questions answered live while the provider waits (D58), saying what they are about (D59).
Nothing here is drawn from anything but the wire — the page is a reader of the record, which is
the point of having one. The shape is the one every serious agent UI converges on: an assistant
turn is a sequence of parts inside the conversation; the side panel is for what changed.

It binds to loopback only. It is an example, not a product: no accounts, one conversation.
"""
