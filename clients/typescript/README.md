# shadow-hdk-client

Types generated from the harness's published schemas (`schemas/*.json` → `src/schemas/*.ts`,
one module per contract; `src/schemas.ts` the barrel), and a thin hand-written client for
`shadow-hdk serve --http`: JSON-RPC over `POST /rpc`, the runtime's replies and notifications
down an SSE stream from `GET /rpc`.

Each received `item` includes the component's bounded JSON `inputs`; an explicit omission marker
replaces values whose canonical encoding exceeds 64 KiB. The client does not reconstruct inputs
from events.

```ts
import { HarnessClient } from "shadow-hdk-client";

const client = new HarnessClient({ address: "http://127.0.0.1:8765", silenceSeconds: 45 });
await client.connect();
const started = await client.thread.start({});
client.approvals.onRequest((request) => client.approvals.answer(request.handle, { kind: "approve" }));
for await (const line of client.turn.start(started.thread_id, "hello from typescript")) {
  if (line.kind === "item") console.log(line.item.step, line.item.outcome);
  if (line.kind === "activity") process.stdout.write(line.activity.text);
  if (line.kind === "done") console.log(line.turn.text);
}
await client.thread.setMode(started.thread_id, "read-only");
const files = await client.files.list(started.thread_id);
```

## Tools as code

A host writes its tools as functions here, and the runtime calls them back — on the thread door,
where a product lives (D21, ENH-030/031). `tool()` makes a function a component in the kit's
published shape: an honest effect profile the mode judges (the same words a battery document
uses — scopes as lists or `"everything"`, the rest booleans), an interface from a JSON schema, a
provenance that says whose it is. `components.serve` answers the runtime's two callbacks for it;
`thread.start({ host_components: true })` offers the tools beside the served composition's. The
runtime judges, admits and records the act exactly as it would a component in its own process;
this side only runs the function.

```ts
import { HarnessClient, tool, Refusal } from "shadow-hdk-client";

const client = new HarnessClient({ address: "http://127.0.0.1:8765" });
client.components.serve([
  tool("find_claims", { description: "Claims about a topic.", effects: { reads: ["record"] },
                        input: { type: "object", properties: { topic: { type: "string" } } } },
       async ({ topic }) => ({ claims: await db.search(String(topic)) })),
  tool("propose_claim", { description: "Put a claim on the record.", effects: { writes: ["record"], reversible: true } },
       async ({ statement }, { run_id }) => {
         if (!statement) throw new Refusal("a claim needs a statement");
         return await db.insert(String(statement), run_id);
       }),
]);
await client.connect();
const started = await client.thread.start({ host_components: true });
```

A thread outlives a connection: a host that goes away takes its tools with it, by name — the
catalogue drops them and an act in flight ends `failed` naming the host — and a new connection's
`thread.resume(id, { host_components: true })` brings its own. An irreversible tool declared here
is recorded with posture `observed`: the runtime never held its authority boundary (D99–D104).
`tools/list` names these tools with `source: "host"`.

## The sidecar — a runtime this process starts

From Node, `shadow-hdk-client/node` starts the runtime as a child and speaks JSON-RPC over its
stdio — the same framing as `shadow-hdk serve --stdio`, MCP's stdio transport and ACP:

```ts
import { spawnHarness } from "shadow-hdk-client/node";
import { tool } from "shadow-hdk-client";

const client = await spawnHarness({
  command: "uvx",
  args: ["--from", "shadow-hdk==0.32.0", "shadow-hdk", "serve", "harness.toml", "--stdio"],
});
client.components.serve([tool("greet", { description: "Greet.", effects: {} }, async ({ name }) => ({ greeting: `hello, ${name}` }))]);
const started = await client.thread.start({ host_components: true });
// … turns as over HTTP …
client.close(); // ends the runtime and its tree
```

**What is spawned is a command you name, and today it needs `uv` on the machine.** That is the
honest state: the kit is a Python distribution, so the documented default runs it through `uvx`.
The pinned, no-prerequisite binary per OS — the interpreter inside, nothing to install first — is
Epic 0010's (cross-platform), Phase 42. When it lands, the `command` becomes that binary and
nothing else here changes.

The server emits a heartbeat comment after 15 seconds idle. If no bytes arrive for
`silenceSeconds` (45 by default), the client cancels the silent response and reattaches with the
last received event id. Set it to `0` only when another layer owns liveness detection. Reconnect
status is available through `onStream`; an expired replay cursor is terminal rather than silently
skipping frames.

A package a product installs. From a checkout, by path — `"shadow-hdk-client":
"file:../path/to/shadow-hdk/clients/typescript"` — after `npm install` here (never `-g`), which
builds `dist/` (`prepare`); `main`, `types` and `exports` point at it. `npm run generate` after
the schemas change, `npm run check`, `npm run build`. The invariant `tests/invariants/test_the_typescript_client_is_current.py`
diffs the generated types against the schemas; `tests/serve/test_the_typescript_client_talks_to_serve.py`
drives a real `serve --http` with this client; `tests/serve/test_a_typescript_host_serves_tools.py`
drives `host-tools-smoke.ts` — a tool served from here, called back over HTTP and over a spawned
stdio runtime. Private — not published.
