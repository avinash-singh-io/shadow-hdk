// A transport carries JSON-RPC frames between this client and a runtime; the client neither knows
// nor cares which. HTTP is the served shape (the session *is* the SSE stream; the host's calls and
// its replies to the runtime's callbacks go up by POST — the split MCP's streamable HTTP uses). A
// sidecar over stdio is in `node.js`, because it needs `node:child_process` and this file must load
// in a browser.
import type { JsonValue } from "./client.js";

const SESSION_HEADER = "x-shadow-hdk-session";

/** Frames in, frames out. `open` resolves once frames can flow; `onFrame` receives every inbound one. */
export interface Transport {
  open(onFrame: (frame: JsonValue) => Promise<void>): Promise<void>;
  send(frame: JsonValue): Promise<void>;
  close(): void;
  /** Told when the link drops for good, so the client can fail what is still waiting. */
  onLost?: (reason: string) => void;
}

export interface HttpTransportOptions {
  /** `http://127.0.0.1:8765` — loopback unless a token is set, as the server requires. */
  address: string;
  /** Sent as `Authorization: Bearer <token>` when the server was started with one. */
  token?: string;
  fetch?: typeof fetch;
  /** Reattach to the same session when the stream drops (D94) — replaying what was missed —
   *  retrying for about this long before giving up (default 60 s, the server's grace). `0` never
   *  reconnects. */
  reconnectSeconds?: number;
  /** Treat an attached stream with no bytes for this long as dropped and reattach it. Defaults
   *  to 45 s (three server heartbeat intervals); `0` disables silence detection. */
  silenceSeconds?: number;
  /** Told when the stream drops and when it is back, and when the session is gone for good. */
  onStream?: (state: "reconnecting" | "connected" | "lost") => void;
}

export class HttpTransport implements Transport {
  private readonly address: string;
  private readonly token?: string;
  private readonly doFetch: typeof fetch;
  private readonly reconnectSeconds: number;
  private readonly silenceSeconds: number;
  private readonly onStream?: HttpTransportOptions["onStream"];
  private sessionId: string | null = null;
  private lastEventId: number | null = null;
  private abort = new AbortController();
  private onFrame: ((frame: JsonValue) => Promise<void>) | null = null;
  onLost?: (reason: string) => void;

  constructor(options: HttpTransportOptions) {
    this.address = options.address.replace(/\/$/, "");
    this.token = options.token;
    // Called as `this.doFetch(...)`, a `fetch` stored bare would run with `this` bound to the
    // transport — a browser refuses that ("Illegal invocation"); Node lets it pass. So the stored
    // function calls the real one with no `this` at all, the supplied one included.
    const underlying = options.fetch ?? fetch;
    this.doFetch = (input, init) => underlying(input, init);
    this.reconnectSeconds = options.reconnectSeconds ?? 60;
    this.silenceSeconds = options.silenceSeconds ?? 45;
    this.onStream = options.onStream;
  }

  /** Open the SSE stream, which *is* the session. */
  open(onFrame: (frame: JsonValue) => Promise<void>): Promise<void> {
    this.onFrame = onFrame;
    return new Promise<void>((resolve, reject) => {
      void this.readForever(resolve, reject);
    });
  }

  close(): void {
    this.abort.abort();
  }

  async send(frame: JsonValue): Promise<void> {
    const response = await this.doFetch(`${this.address}/rpc`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(frame),
    });
    if (response.status !== 202) throw new Error(`posting a frame: ${response.status}`);
  }

  private headers(): Record<string, string> {
    const headers: Record<string, string> = { "content-type": "application/json" };
    if (this.token) headers.authorization = `Bearer ${this.token}`;
    if (this.sessionId) headers[SESSION_HEADER] = this.sessionId;
    return headers;
  }

  private async readForever(ready: () => void, failed: (e: Error) => void): Promise<void> {
    let response: Response;
    try {
      response = await this.doFetch(`${this.address}/rpc`, { headers: this.headers(), signal: this.abort.signal });
    } catch (error) {
      failed(error as Error);
      return;
    }
    if (!response.ok || !response.body) {
      failed(new Error(`opening the session: ${response.status}`));
      return;
    }
    this.sessionId = response.headers.get(SESSION_HEADER);
    ready();
    await this.readStream(response.body);
    // The stream ended and we did not close it: the session is still there for a while (D94).
    // Reattach with the last frame seen, replaying what was missed; give up when the server
    // says the session is gone, or after the grace.
    while (!this.abort.signal.aborted && this.reconnectSeconds > 0) {
      this.onStream?.("reconnecting");
      const body = await this.reattach();
      if (body === null) break;
      this.onStream?.("connected");
      await this.readStream(body);
    }
    if (!this.abort.signal.aborted) {
      this.onStream?.("lost");
      this.onLost?.("the stream ended and the session is gone");
    }
  }

  /** `GET /rpc` with the session header and `Last-Event-ID`, retried with a widening pause for
   *  about `reconnectSeconds`; `null` when the session is gone (404) or the time is up. */
  private async reattach(): Promise<ReadableStream<Uint8Array> | null> {
    const deadline = Date.now() + this.reconnectSeconds * 1000;
    let pause = 500;
    while (Date.now() < deadline && !this.abort.signal.aborted) {
      try {
        const headers = this.headers();
        if (this.lastEventId !== null) headers["last-event-id"] = String(this.lastEventId);
        const response = await this.doFetch(`${this.address}/rpc`, { headers, signal: this.abort.signal });
        if (response.status === 404 || response.status === 410) return null;
        if (response.ok && response.body) return response.body;
      } catch {
        // not reachable yet: wait and try again
      }
      await new Promise((r) => setTimeout(r, pause));
      pause = Math.min(pause * 2, 5000);
    }
    return null;
  }

  private async readStream(body: ReadableStream<Uint8Array>): Promise<void> {
    const decoder = new TextDecoder();
    const reader = body.getReader();
    let buffer = "";
    try {
      for (;;) {
        const { value, done } = await this.readBeforeSilence(reader);
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let cut: number;
        while ((cut = buffer.indexOf("\n\n")) >= 0) {
          const frame = buffer.slice(0, cut);
          buffer = buffer.slice(cut + 2);
          for (const line of frame.split("\n")) {
            if (line.startsWith("id: ")) this.lastEventId = Number(line.slice(4));
            else if (line.startsWith("data: ")) await this.onFrame?.(JSON.parse(line.slice(6)) as JsonValue);
          }
        }
      }
    } catch (error) {
      if (!this.abort.signal.aborted) {
        try {
          await reader.cancel("the stream was silent or broken");
        } catch {
          // The transport already ended while it was being cancelled; reattach all the same.
        }
        return; // the stream broke or went silent: the caller reattaches
      }
    }
  }

  private readBeforeSilence(
    reader: ReadableStreamDefaultReader<Uint8Array>,
  ): Promise<ReadableStreamReadResult<Uint8Array>> {
    if (this.silenceSeconds <= 0) return reader.read();
    return new Promise((resolve, reject) => {
      const timer = setTimeout(
        () => reject(new Error("the stream exceeded its silence deadline")),
        this.silenceSeconds * 1000,
      );
      reader.read().then(
        (result) => {
          clearTimeout(timer);
          resolve(result);
        },
        (error: unknown) => {
          clearTimeout(timer);
          reject(error);
        },
      );
    });
  }
}
