// ENH-031: a host writes its tools as code in TypeScript and the runtime calls them back on the
// thread door. Driven by the Python suite (tests/serve/test_a_typescript_host_serves_tools.py)
// two ways — over HTTP against a live `serve --http`, and over stdio against a runtime this
// process spawns — and prints one JSON line with what it saw.
//
//   node host-tools-smoke.js http  http://127.0.0.1:PORT
//   node host-tools-smoke.js stdio <command> [args...]
import { HarnessClient, tool } from "./client.js";

const how = process.argv[2];
const client =
  how === "stdio"
    ? await HarnessClient.spawn({ command: process.argv[3], args: process.argv.slice(4) })
    : new HarnessClient({ address: process.argv[3] });

const greeted: unknown[] = [];
client.components.serve([
  tool(
    "greet",
    { description: "Greet someone by name.", effects: {}, input: { type: "object", properties: { name: { type: "string" } } } },
    async ({ name }) => {
      greeted.push(name);
      return { greeting: `hello, ${String(name)} — from typescript` };
    },
  ),
]);

await client.connect();
const started = await client.thread.start({ host_components: true });
const tools = await client.tools.list(started.thread_id);
const greet = tools.tools.find((t) => t.id === "greet");
let observed: unknown = null;
let text = "";
for await (const line of client.turn.start(started.thread_id, "greet typescript")) {
  if (line.kind === "done") text = line.turn.text;
  if (line.kind === "event" && line.event.kind === "observed" && greeted.length) observed = line.event.observation;
}
await client.thread.close(started.thread_id);
await client.close();
console.log(JSON.stringify({ how, source: greet?.source ?? null, greeted, observed, text }));
