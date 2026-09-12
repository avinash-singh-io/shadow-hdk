// A smoke run of the client against a live `shadow-hdk serve --http`, driven by the Python
// test suite (tests/serve/test_the_typescript_client_talks_to_serve.py), which starts the server
// with a scripted provider and passes its address. The body is the README's snippet, run for
// real. Prints one JSON line with what it saw.
import { HarnessClient } from "./client.js";

const address = process.argv[2];
if (!address) {
  console.error("usage: node smoke.js http://127.0.0.1:PORT [token]");
  process.exit(2);
}
const client = new HarnessClient({ address, token: process.argv[3] });
await client.connect();
const started = await client.thread.start({ mode: "workspace-write" });
client.approvals.onRequest((request) => client.approvals.answer(request.handle, { kind: "approve" }));
const seen: string[] = [];
let text = "";
for await (const line of client.turn.start(started.thread_id, "hello from typescript")) {
  if (line.kind === "done") text = line.turn.text;
  else if (line.kind === "item") seen.push(`item:${line.item.step}`);
  else if (line.kind === "event") seen.push(`event:${line.event.kind}`);
  else seen.push(`activity:${line.activity.kind}`);
}
const changed = await client.thread.setMode(started.thread_id, "read-only");
const files = await client.files.list(started.thread_id);
const modes = await client.modes.list();
const version = await client.store.version("modes");
await client.thread.close(started.thread_id);
client.close();
console.log(
  JSON.stringify({
    thread_id: started.thread_id,
    root: started.root,
    provider: started.provider,
    text,
    seen,
    mode_events: changed.events.map((e) => e.kind),
    files: files.files.map((f) => f.path),
    modes: modes.modes.map((m) => m.id),
    version: version.version,
  }),
);
