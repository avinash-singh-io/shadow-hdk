// A thin client for `shadow-hdk serve --http` (D67, D68): JSON-RPC over `POST /rpc`, the
// runtime's replies and notifications down an SSE stream from `GET /rpc`. One session per client;
// the session id arrives in the `x-shadow-hdk-session` response header and travels back on every POST.
//
// Hand-written on purpose: the *types* are generated from the published schemas (src/schemas/),
// the *protocol* is the methods a product calls, and a client that hides them behind a
// framework would be one more thing to keep in step.

import type { Event } from "./schemas/Event.js";
import type { Item } from "./schemas/Item.js";
import type { Activity } from "./schemas/Activity.js";

export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

export interface ClientOptions {
  /** `http://127.0.0.1:8765` — loopback unless a token is set, as the server requires. */
  address: string;
  /** Sent as `Authorization: Bearer <token>` when the server was started with one. */
  token?: string;
  /** Answer the runtime's own requests (a component on this side). Rarely needed for threads. */
  onRequest?: (method: string, params: JsonValue) => Promise<JsonValue>;
  fetch?: typeof fetch;
}

export interface ApprovalRequest {
  handle: string;
  run_id: string;
  step: string;
  question: string;
  component: string | null;
  inputs: JsonValue;
  kind: "approval" | "input";
}

export type Answer =
  | { kind: "approve" }
  | { kind: "deny"; reason?: string }
  | { kind: "approve_and_add_rule"; rule: { component: string; inputs?: Record<string, JsonValue>; decision?: "allow" | "deny"; mode?: string; note?: string } }
  | { text: string };

export interface TurnRecord {
  id: string;
  run_id: string;
  prompt: string;
  at: string;
  outcome: "running" | "completed" | "failed" | "refused" | "cancelled" | "parked";
  text: string;
}

export type TurnLine =
  | { kind: "event"; thread_id: string; event: Event }
  | { kind: "item"; thread_id: string; item: Item }
  | { kind: "activity"; thread_id: string; activity: Activity };

export interface Started {
  thread_id: string;
  /** The workspace the thread's tools act in — what `files.list` and `files.read` are under. */
  root: string;
  provider: string;
  mode: string;
  modes: { id: string; name: string; description: string; source: string }[];
}

export interface Resumed extends Started {
  turns: TurnRecord[];
}

export interface BatteryRow {
  id: string;
  name: string;
  kind: string;
  source: string;
  tools: string[];
  licence: string;
  status: "on" | "off" | "unavailable";
  problem: string | null;
}

export interface OfferedTool {
  id: string;
  name: string;
  description: string;
  effects: { reads: Scope; writes: Scope; reaches: boolean; reversible: boolean; contained: boolean; costs: boolean };
  /** `allow` · `ask` · `refuse` — a refused one is absent from the model's catalogue. */
  judgement: "allow" | "ask" | "refuse";
  /** The port that carried it: `LocalEnvironment`, `SkillComponents`, a battery's adapter. */
  source: string;
  registration: JsonValue;
}

export interface Scope {
  names: string[];
  everything: boolean;
}

export interface SkillEntry {
  name: string;
  description: string;
  needs: string[];
  source: string;
}

export interface FileEntry {
  path: string;
  bytes: number;
  mtime: number;
}

const SESSION_HEADER = "x-shadow-hdk-session";

type Pending = { resolve: (value: JsonValue) => void; reject: (reason: Error) => void };

export class HarnessClient {
  private readonly address: string;
  private readonly token?: string;
  private readonly onRequest?: ClientOptions["onRequest"];
  private readonly doFetch: typeof fetch;
  private sessionId: string | null = null;
  private nextId = 1;
  private readonly pending = new Map<number, Pending>();
  private readonly listeners = new Map<string, Set<(params: JsonValue) => void>>();
  private reader: Promise<void> | null = null;
  private abort = new AbortController();

  constructor(options: ClientOptions) {
    this.address = options.address.replace(/\/$/, "");
    this.token = options.token;
    this.onRequest = options.onRequest;
    this.doFetch = options.fetch ?? fetch;
  }

  // ---------------------------------------------------------------- the session

  /** Open the SSE stream (which *is* the session) and complete the handshake. */
  async connect(): Promise<void> {
    const opened = new Promise<void>((resolve, reject) => {
      this.reader = this.readForever(resolve, reject);
    });
    await opened;
    await this.call("initialize", { protocol_version: "1" });
  }

  close(): void {
    this.abort.abort();
    for (const waiting of this.pending.values()) waiting.reject(new Error("closed"));
    this.pending.clear();
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
    const decoder = new TextDecoder();
    const reader = response.body.getReader();
    let buffer = "";
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let cut: number;
        while ((cut = buffer.indexOf("\n\n")) >= 0) {
          const frame = buffer.slice(0, cut);
          buffer = buffer.slice(cut + 2);
          for (const line of frame.split("\n")) {
            if (line.startsWith("data: ")) await this.onFrame(JSON.parse(line.slice(6)) as JsonValue);
          }
        }
      }
    } catch (error) {
      if (!this.abort.signal.aborted) throw error;
    }
  }

  private async onFrame(message: JsonValue): Promise<void> {
    if (message === null || typeof message !== "object" || Array.isArray(message)) return;
    const frame = message as { [key: string]: JsonValue };
    if ("method" in frame) {
      const method = String(frame.method);
      const params = (frame.params ?? {}) as JsonValue;
      if ("id" in frame) {
        // The runtime asks *us* — a port on this side. Answer, or say we cannot.
        try {
          const result = this.onRequest ? await this.onRequest(method, params) : null;
          if (!this.onRequest) throw new Error(`no handler on this side for ${method}`);
          await this.post({ jsonrpc: "2.0", id: frame.id, result });
        } catch (error) {
          await this.post({ jsonrpc: "2.0", id: frame.id, error: { code: -32000, message: String(error) } });
        }
        return;
      }
      for (const listener of this.listeners.get(method) ?? []) listener(params);
      return;
    }
    if ("id" in frame && typeof frame.id === "number") {
      const waiting = this.pending.get(frame.id);
      if (!waiting) return;
      this.pending.delete(frame.id);
      if ("error" in frame && frame.error) {
        const error = frame.error as { message?: string };
        waiting.reject(new Error(error.message ?? JSON.stringify(frame.error)));
      } else {
        waiting.resolve((frame.result ?? null) as JsonValue);
      }
    }
  }

  private async post(frame: { [key: string]: JsonValue | undefined }): Promise<void> {
    const response = await this.doFetch(`${this.address}/rpc`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(frame),
    });
    if (response.status !== 202) throw new Error(`posting a frame: ${response.status}`);
  }

  /** One JSON-RPC call; the reply arrives down the SSE stream. */
  async call<T = JsonValue>(method: string, params: { [key: string]: JsonValue } = {}): Promise<T> {
    const id = this.nextId++;
    const answered = new Promise<JsonValue>((resolve, reject) => this.pending.set(id, { resolve, reject }));
    await this.post({ jsonrpc: "2.0", id, method, params });
    return (await answered) as T;
  }

  /** Hear a notification kind (`event`, `item`, `activity`, `approval_request`, `input_request`, `request_withdrawn`). */
  on(method: string, listener: (params: JsonValue) => void): () => void {
    const set = this.listeners.get(method) ?? new Set();
    set.add(listener);
    this.listeners.set(method, set);
    return () => set.delete(listener);
  }

  // ---------------------------------------------------------------- the thread

  readonly thread = {
    start: (params: { root?: string; mode?: string; provider?: string; name?: string; thread_id?: string }) =>
      this.call<Started>("thread/start", params as { [key: string]: JsonValue }),
    resume: (thread_id: string) => this.call<Resumed>("thread/resume", { thread_id }),
    close: (thread_id: string) => this.call<{ closed: string }>("thread/close", { thread_id }),
    list: () => this.call<{ threads: JsonValue[] }>("thread/list", {}),
    fork: (thread_id: string) => this.call<{ thread: JsonValue }>("thread/fork", { thread_id }),
    rollback: (thread_id: string, to_turn: number) => this.call<{ thread: JsonValue }>("thread/rollback", { thread_id, to_turn }),
    archive: (thread_id: string) => this.call<{ archived: string }>("thread/archive", { thread_id }),
    setMode: (thread_id: string, mode: string) => this.call<{ events: Event[] }>("thread/set_mode", { thread_id, mode }),
    setOption: (thread_id: string, key: string, value: JsonValue) => this.call<{ ok: boolean }>("thread/set_option", { thread_id, key, value }),
    remaining: (thread_id: string) => this.call<{ lease: JsonValue }>("thread/remaining", { thread_id }),
  };

  readonly turn = {
    /**
     * Start a turn and iterate what happens — events, items and activity tagged with the thread —
     * until the turn's record comes back as `{ kind: "done", turn }`.
     */
    start: (thread_id: string, text: string): AsyncIterable<TurnLine | { kind: "done"; turn: TurnRecord }> => {
      const queue: (TurnLine | { kind: "done"; turn: TurnRecord })[] = [];
      let wake: (() => void) | null = null;
      const push = (line: TurnLine | { kind: "done"; turn: TurnRecord }) => {
        queue.push(line);
        wake?.();
      };
      const stops = ["event", "item", "activity"].map((kind) =>
        this.on(kind, (params) => {
          const p = params as unknown as { thread_id: string };
          if (p.thread_id === thread_id) push({ kind, ...(params as object) } as TurnLine);
        }),
      );
      let finished = false;
      void this.call<{ turn: TurnRecord }>("turn/start", { thread_id, text })
        .then((result) => push({ kind: "done", turn: result.turn }))
        .catch((error: Error) => push({ kind: "done", turn: { id: "", run_id: "", prompt: text, at: "", outcome: "failed", text: String(error) } }))
        .finally(() => {
          finished = true;
          stops.forEach((stop) => stop());
        });
      return {
        async *[Symbol.asyncIterator]() {
          for (;;) {
            if (queue.length === 0) {
              if (finished) return;
              await new Promise<void>((resolve) => (wake = resolve));
              wake = null;
              continue;
            }
            const next = queue.shift()!;
            yield next;
            if (next.kind === "done") return;
          }
        },
      };
    },
    steer: (thread_id: string, text: string) => this.call<{ taken: "now" | "next" }>("turn/steer", { thread_id, text }),
    interrupt: (thread_id: string) => this.call<{ interrupted: boolean }>("turn/interrupt", { thread_id }),
  };

  readonly approvals = {
    pending: () => this.call<{ requests: ApprovalRequest[] }>("approvals/pending", {}),
    answer: (handle: string, answer: Answer) => this.call<{ answered: boolean }>("approvals/answer", { handle, answer: answer as unknown as JsonValue }),
    /** Requests as they become pending — approvals and the agent's own questions — and withdrawals. */
    onRequest: (listener: (request: ApprovalRequest, thread_id: string) => void) => {
      const off = ["approval_request", "input_request"].map((kind) =>
        this.on(kind, (params) => {
          const p = params as unknown as { thread_id: string; request: ApprovalRequest };
          listener(p.request, p.thread_id);
        }),
      );
      return () => off.forEach((stop) => stop());
    },
    onWithdrawn: (listener: (handle: string, thread_id: string) => void) =>
      this.on("request_withdrawn", (params) => {
        const p = params as unknown as { thread_id: string; handle: string };
        listener(p.handle, p.thread_id);
      }),
  };

  readonly store = {
    put: (collection: string, key: string, row: JsonValue) => this.call<{ ok: boolean }>("store/put", { collection, key, row }),
    get: (collection: string, key: string) => this.call<{ row: JsonValue }>("store/get", { collection, key }),
    delete: (collection: string, key: string) => this.call<{ ok: boolean }>("store/delete", { collection, key }),
    list: (collection: string) => this.call<{ rows: [string, JsonValue][] }>("store/list", { collection }),
    version: (collection: string) => this.call<{ version: number }>("store/version", { collection }),
  };

  /** The thread's workspace, read — under its root only; dotfiles and caches left out (D69). */
  readonly files = {
    list: (thread_id: string) => this.call<{ files: FileEntry[] }>("files/list", { thread_id }),
    read: (thread_id: string, path: string) => this.call<{ content: string }>("files/read", { thread_id, path }),
  };

  /** What the thread's agent is offered now — every registration with the mode's judgement (Phase 28). */
  readonly tools = {
    list: (thread_id: string) => this.call<{ tools: OfferedTool[] }>("tools/list", { thread_id }),
  };
  /** The skills the composition carries — shipped, from the store, minted — with their sources. */
  readonly skills = { list: () => this.call<{ skills: SkillEntry[] }>("skills/list", {}) };

  readonly modes = { list: () => this.call<{ modes: Started["modes"] }>("modes/list", {}) };
  /** What the serving process has switched on (D70): every battery, on · off · unavailable and why. */
  readonly batteries = { list: () => this.call<{ batteries: BatteryRow[] }>("batteries/list", {}) };
  readonly rules = { list: () => this.call<{ rules: JsonValue[] }>("rules/list", {}) };
  readonly run = { cancel: (thread_id: string) => this.call<{ cancelled: boolean }>("run/cancel", { thread_id }) };
}
