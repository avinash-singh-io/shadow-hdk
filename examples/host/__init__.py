"""A host — any program that consumes the runtime in-process.

    uv run python -m examples.host "brief" [--brain=script|key|subscription] [--root=DIR]

The coder example is a *conversation*; this is a **host**: a program with its own policy, its own
record, its own durable store and its own view, that hands all four to the runtime and runs a brief
through whichever reasoning it has. It is not named for any product because it is the shape every
product takes.

What it hands in:

* `Policy` — its own `GovernancePort`, a judgement over **effects** (D5): reads anywhere, writes in
  the workspace, a write outside is a **question** for the host, the network is refused.
* `Ledger` — its own `SinkPort`: what the run proposed, kept, and dumped as JSON at the end.
* a checkpointer — LangGraph's, on a file, so a run parked on a question survives the process
  that parked it and is resumed by the next one (the runtime owns nothing durable — 09 §6).
* the projection rendered — every step, what was thought first, what it cost, nested by run.
* a brain — a scripted model (the proof, costs nothing), a model **by key** (any provider
  LangChain integrates) or a CLI **by subscription** (whatever is signed in on this machine). The
  host chooses; the run is the same.
"""
