# shadow-hdk-client

Types generated from the harness's published schemas (`schemas/*.json` → `src/schemas/*.ts`,
one module per contract; `src/schemas.ts` the barrel), and a thin hand-written client for
`shadow-hdk serve --http`: JSON-RPC over `POST /rpc`, the runtime's replies and notifications
down an SSE stream from `GET /rpc`.

```ts
import { HarnessClient } from "shadow-hdk-client";

const client = new HarnessClient({ address: "http://127.0.0.1:8765" });
await client.connect();
const { thread_id } = await client.thread.start({ mode: "workspace-write" });
client.approvals.onRequest((request) => client.approvals.answer(request.handle, { kind: "approve" }));
for await (const line of client.turn.start(thread_id, "add a .gitignore and run the tests")) {
  if (line.kind === "item") console.log(line.item.step, line.item.outcome);
  if (line.kind === "activity") process.stdout.write(line.activity.text);
  if (line.kind === "done") console.log(line.turn.text);
}
await client.thread.setMode(thread_id, "read-only");
```

Local only: `npm install` here (never `-g`), `npm run generate` after the schemas change,
`npm run check`, `npm run build`. The invariant `tests/invariants/test_the_typescript_client_is_current.py`
diffs the generated types against the schemas; `tests/serve/test_the_typescript_client_talks_to_serve.py`
drives a real `serve --http` with this client. Private — not published.
