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
import type { ExecutionRequirements } from "./schemas/ExecutionRequirements.js";
import type { ExecutionSelection } from "./schemas/ExecutionSelection.js";
import type { ProviderCapabilities } from "./schemas/ProviderCapabilities.js";
import { PROTOCOL_VERSION } from "./schemas.js";

export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

export interface ClientOptions {
  /** `http://127.0.0.1:8765` — loopback unless a token is set, as the server requires. */
  address: string;
  /** Sent as `Authorization: Bearer <token>` when the server was started with one. */
  token?: string;
  /** Answer the runtime's own requests (a component on this side). Rarely needed for threads. */
  onRequest?: (method: string, params: JsonValue) => Promise<JsonValue>;
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

export interface ApprovalRequest {
  handle: string;
  run_id: string;
  step: string;
  question: string;
  component: string | null;
  inputs: JsonValue;
  kind: "approval" | "input";
  /** Set on a question the last host left open (D80): the turn it belongs to. */
  turn?: string;
}

export type Answer =
  | { kind: "approve" }
  | { kind: "deny"; reason?: string }
  /** Not now (D88): the call is kept with the run that sleeps on it; answer it later, on any request. */
  | { kind: "park" }
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

export interface RootEntry {
  name: string;
  path: string;
}

export interface Started {
  thread_id: string;
  /** The primary root's path — what a one-root reader expects; `roots` is the whole workspace. */
  root: string;
  /** The workspace (D76): one or many roots, the first the primary; the rest addressed `name/path`. */
  roots: RootEntry[];
  /** The environment's own mode — what the sandbox enforces — beside `mode`, the policy's. */
  environment: string;
  /**
   * The behaviour fields the mode set that the provider could not take (ENH-020) — `system` or
   * `model` on a CLI whose record maps no flag for them. Named so a host hides the control.
   */
  unmapped_behaviour: string[];
  provider: string;
  mode: string;
  modes: { id: string; name: string; description: string; source: string; scope: string }[];
  /** Who the thread is for, and the product's words about it (D82). */
  principal: string;
  attributes: { [key: string]: JsonValue };
  /** The exact provider/environment facts accepted for this thread. */
  capabilities: ExecutionSelection;
}

export interface ProviderRow {
  id: string;
  name: string;
  kind: "model" | "agent";
  status: "ready" | "absent" | "not-signed-in" | "too-old" | "unknown";
  binary: string | null;
  version: string | null;
  message: string | null;
  install_hint: string;
  capabilities: ProviderCapabilities;
}

export interface Resumed extends Started {
  turns: TurnRecord[];
  /** Questions the last host left open (D80), offered again — answer them like any other. */
  pending: ApprovalRequest[];
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
  /** Which root the file is under. */
  root: string;
  path: string;
  bytes: number;
  mtime: number;
}

const SESSION_HEADER = "x-shadow-hdk-session";

type Pending = { resolve: (value: JsonValue) => void; reject: (reason: Error) => void };

/** What `error.data.kind` may say (D92) — the vocabulary a page switches on. */
export type ErrorKind =
  | "thread_held"
  | "turn_running"
  | "capability_mismatch"
  | "not_found"
  | "invalid"
  | "version_mismatch"
  | "unknown_method"
  | "refused"
  | "gone";

/** The harness refused or failed a call: its code, its sentence, and a `kind` to switch on
 *  with the detail a page acts on — a held thread's `holder`, a running turn's `turn_id`. */
export class RemoteError extends Error {
  readonly code: number;
  readonly kind: ErrorKind;
  readonly detail: { [key: string]: JsonValue };
  constructor(code: number, message: string, data: JsonValue) {
    super(message);
    this.name = "RemoteError";
    this.code = code;
    const record = data && typeof data === "object" && !Array.isArray(data) ? data : {};
    const { kind, ...detail } = record as { kind?: ErrorKind } & { [key: string]: JsonValue };
    this.kind = kind ?? "refused";
    this.detail = detail;
  }
}

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
  private lastEventId: number | null = null;
  private readonly reconnectSeconds: number;
  private readonly silenceSeconds: number;
  private readonly onStream?: ClientOptions["onStream"];

  constructor(options: ClientOptions) {
    this.address = options.address.replace(/\/$/, "");
    this.token = options.token;
    this.onRequest = options.onRequest;
    // Called as `this.doFetch(...)`, a `fetch` stored bare would run with `this` bound to the
    // client — a browser refuses that ("Illegal invocation"); Node lets it pass. So the stored
    // function calls the real one with no `this` at all, the supplied one included.
    const underlying = options.fetch ?? fetch;
    this.doFetch = (input, init) => underlying(input, init);
    this.reconnectSeconds = options.reconnectSeconds ?? 60;
    this.silenceSeconds = options.silenceSeconds ?? 45;
    this.onStream = options.onStream;
  }

  // ---------------------------------------------------------------- the session

  /** Open the SSE stream (which *is* the session) and complete the handshake. */
  async connect(): Promise<void> {
    const opened = new Promise<void>((resolve, reject) => {
      this.reader = this.readForever(resolve, reject);
    });
    await opened;
    await this.call("initialize", { protocol_version: PROTOCOL_VERSION });
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
      for (const waiting of this.pending.values()) waiting.reject(new Error("the stream ended and the session is gone"));
      this.pending.clear();
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
            else if (line.startsWith("data: ")) await this.onFrame(JSON.parse(line.slice(6)) as JsonValue);
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
        const error = frame.error as { code?: number; message?: string; data?: JsonValue };
        waiting.reject(new RemoteError(error.code ?? -32000, error.message ?? JSON.stringify(frame.error), error.data ?? null));
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
    /** `principal` and `attributes` (D82): who the thread is for and the product's words about it — on the record and every judgement. */
    start: (params: {
      root?: string;
      roots?: RootEntry[];
      mode?: string;
      provider?: string;
      name?: string;
      thread_id?: string;
      principal?: string;
      attributes?: { [key: string]: JsonValue };
      /** This thread's own ceiling over the file's default (D84); what it spends is on its record. */
      budget?: { steps?: number; seconds?: number; cents?: number | null };
      requirements?: ExecutionRequirements;
    }) => this.call<Started>("thread/start", params as unknown as { [key: string]: JsonValue }),
    resume: (thread_id: string) => this.call<Resumed>("thread/resume", { thread_id }),
    close: (thread_id: string) => this.call<{ closed: string }>("thread/close", { thread_id }),
    /** Every thread in the store; `held_by` names the process that has it open (D81), or is null. */
    list: () => this.call<{ threads: (JsonValue & { held_by?: string | null })[] }>("thread/list", {}),
    fork: (thread_id: string) => this.call<{ thread: JsonValue }>("thread/fork", { thread_id }),
    rollback: (thread_id: string, to_turn: number) => this.call<{ thread: JsonValue }>("thread/rollback", { thread_id, to_turn }),
    archive: (thread_id: string) => this.call<{ archived: string }>("thread/archive", { thread_id }),
    setMode: (thread_id: string, mode: string) =>
      this.call<{ events: Event[]; environment: string; unmapped_behaviour: string[] }>("thread/set_mode", { thread_id, mode }),
    /** A directory added while the thread runs (D76): the sandbox re-proven over the new set. */
    addRoot: (thread_id: string, name: string, path: string) =>
      this.call<{ events: Event[]; root: string; roots: RootEntry[]; environment: string; unmapped_behaviour: string[] }>("thread/add_root", { thread_id, name, path }),
    setOption: (thread_id: string, key: string, value: JsonValue) => this.call<{ ok: boolean }>("thread/set_option", { thread_id, key, value }),
    remaining: (thread_id: string) => this.call<{ lease: JsonValue }>("thread/remaining", { thread_id }),
  };

  readonly turn = {
    /**
     * Start a turn and iterate what happens — events, items and activity tagged with the thread —
     * until the turn's record comes back as `{ kind: "done", turn }`.
     */
    start: (
      thread_id: string,
      text: string,
      options: { when?: "enqueue" | "reject" | "interrupt"; on_question?: "wait" | "park" } = {},
    ): AsyncIterable<TurnLine | { kind: "done"; turn: TurnRecord }> => {
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
      void this.call<{ turn: TurnRecord }>("turn/start", {
        thread_id,
        text,
        ...(options.when ? { when: options.when } : {}),
        ...(options.on_question ? { on_question: options.on_question } : {}),
      })
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
    /** `events` comes back when the question was one the last host left (D80): the parked act ran from its checkpoint. */
    answer: (handle: string, answer: Answer) =>
      this.call<{ answered: boolean; events?: Event[] }>("approvals/answer", { handle, answer: answer as unknown as JsonValue }),
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
    read: (thread_id: string, path: string, root?: string) =>
      this.call<{ content: string }>("files/read", root ? { thread_id, root, path } : { thread_id, path }),
  };

  /** What the thread's agent is offered now — every registration with the mode's judgement (Phase 28). */
  readonly tools = {
    list: (thread_id: string) => this.call<{ tools: OfferedTool[] }>("tools/list", { thread_id }),
  };
  /** The skills the composition carries — shipped, from the store, minted — with their sources. */
  readonly skills = { list: () => this.call<{ skills: SkillEntry[] }>("skills/list", {}) };

  /** Every mode, or — with a thread — the ones in that thread's scope (D82). */
  readonly modes = { list: (thread_id?: string) => this.call<{ modes: Started["modes"] }>("modes/list", thread_id ? { thread_id } : {}) };
  /** What the serving process has switched on (D70): every battery, on · off · unavailable and why. */
  readonly batteries = { list: () => this.call<{ batteries: BatteryRow[] }>("batteries/list", {}) };
  /** Providers this process can detect, with evidence-backed execution facts. */
  readonly providers = {
    list: () => this.call<{ providers: ProviderRow[] }>("providers/list", {}),
  };
  /** Prove a provider/environment pair without opening an agent or a thread. */
  readonly capabilities = {
    check: (params: { root?: string; mode?: string; provider?: string; requirements?: ExecutionRequirements }) =>
      this.call<{ capabilities: ExecutionSelection }>("capabilities/check", params as unknown as { [key: string]: JsonValue }),
  };
  /** Every rule, or — with a thread — the ones in that thread's scope (D82). */
  readonly rules = { list: (thread_id?: string) => this.call<{ rules: JsonValue[] }>("rules/list", thread_id ? { thread_id } : {}) };
  readonly run = { cancel: (thread_id: string) => this.call<{ cancelled: boolean }>("run/cancel", { thread_id }) };
  /** What the process holds, for its operator (D86): every session and every thread, behind the bearer. */
  readonly admin = {
    sessions: () => this.call<{ sessions: { id: string; opened_at: string; threads: string[] }[] }>("admin/sessions", {}),
    threads: () => this.call<{ threads: JsonValue[] }>("admin/threads", {}),
  };
}
