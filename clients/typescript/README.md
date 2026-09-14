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
drives a real `serve --http` with this client. Private — not published.
