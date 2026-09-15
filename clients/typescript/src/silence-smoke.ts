// A link that remains open but emits no bytes is broken from a browser's point of view. The
// client must abort only that GET, retain the session cursor, and reattach through the ordinary
// D94 path. This fake transport makes the silence deterministic without a timing-sensitive server.
import { HarnessClient } from "./client.js";

const encoder = new TextEncoder();
const states: string[] = [];
const controllers: ReadableStreamDefaultController<Uint8Array>[] = [];
let firstController: ReadableStreamDefaultController<Uint8Array> | null = null;
let gets = 0;
let reattachCursor: string | null = null;

const fakeFetch: typeof fetch = async (_input, init = {}) => {
  const method = init.method ?? "GET";
  if (method === "POST") {
    const request = JSON.parse(String(init.body)) as { id: number };
    firstController?.enqueue(
      encoder.encode(
        `id: 1\ndata: ${JSON.stringify({ jsonrpc: "2.0", id: request.id, result: { protocol_version: 2 } })}\n\n`,
      ),
    );
    return new Response(null, { status: 202 });
  }

  gets += 1;
  const headers = new Headers(init.headers);
  if (gets > 1) reattachCursor = headers.get("last-event-id");
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controllers.push(controller);
      if (gets === 1) firstController = controller;
      controller.enqueue(encoder.encode(": session open\n\n"));
      init.signal?.addEventListener(
        "abort",
        () => controller.error(new Error("connection aborted")),
        { once: true },
      );
    },
  });
  return new Response(body, {
    status: 200,
    headers: { "x-shadow-hdk-session": "session-1" },
  });
};

const client = new HarnessClient({
  address: "http://shadow.invalid",
  fetch: fakeFetch,
  reconnectSeconds: 1,
  silenceSeconds: 0.02,
  onStream: (state) => states.push(state),
});

await client.connect();
const deadline = Date.now() + 1000;
while (!states.includes("connected") && Date.now() < deadline) {
  await new Promise((resolve) => setTimeout(resolve, 5));
}
client.close();

if (gets < 2 || !states.includes("reconnecting") || !states.includes("connected")) {
  throw new Error(`silent stream did not reattach: ${JSON.stringify({ gets, states })}`);
}
if (reattachCursor !== "1") {
  throw new Error(`reattach lost the last event id: ${String(reattachCursor)}`);
}
console.log(JSON.stringify({ gets, states, reattachCursor, streams: controllers.length }));
