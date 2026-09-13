# `shadow_hdk.adapters.recording`

The mirror of the ACP bridge. That lets a child agent ask **us** for things; this offers **our**
registry to the child as an MCP server.

The handler does not re-implement judging or eventing. It calls `run()` with a one-step composition,
as a child of the parent run — so judgement, the event stream, lease carving and provenance all
arrive because they are what a run already does.

> Recording is a consequence of routing.
