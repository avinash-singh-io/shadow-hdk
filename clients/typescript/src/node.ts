// The sidecar door, Node only: start the runtime as a child process and speak JSON-RPC over its
// stdio — newline-delimited JSON, the same framing `shadow-hdk serve --stdio`, MCP's stdio transport
// and ACP use. Imported from `shadow-hdk-client/node` so the browser build never sees
// `node:child_process`.
//
// **What is spawned is a command you name.** Until Epic 0010 (cross-platform) ships the kit as one
// artifact per OS with the interpreter inside, the documented default needs `uv` on the machine:
//
//     uvx --from shadow-hdk==<version> shadow-hdk serve harness.toml --stdio
//
// That prerequisite is stated, not hidden; the pinned, no-prerequisite binary lands in Phase 42.
import { spawn, type ChildProcess } from "node:child_process";
import { HarnessClient, type JsonValue } from "./client.js";
import type { Transport } from "./transport.js";

export interface SpawnOptions {
  /** The runtime's command — `shadow-hdk`, `uvx`, `python` — resolved on PATH or absolute. */
  command: string;
  args?: string[];
  cwd?: string;
  env?: NodeJS.ProcessEnv;
  /** Answer the runtime's own requests beyond components (rare). */
  onRequest?: (method: string, params: JsonValue) => Promise<JsonValue>;
  /** Seconds to wait after SIGTERM before SIGKILL on `close()` (default 5). */
  graceSeconds?: number;
  /** The child's stderr, line by line — the runtime's own logging. Default: forwarded to this process's stderr. */
  onStderr?: (line: string) => void;
}

export class StdioTransport implements Transport {
  private child: ChildProcess | null = null;
  private onFrame: ((frame: JsonValue) => Promise<void>) | null = null;
  private closing = false;
  onLost?: (reason: string) => void;

  constructor(private readonly options: SpawnOptions) {}

  async open(onFrame: (frame: JsonValue) => Promise<void>): Promise<void> {
    this.onFrame = onFrame;
    const child = spawn(this.options.command, this.options.args ?? [], {
      cwd: this.options.cwd,
      env: this.options.env ?? process.env,
      stdio: ["pipe", "pipe", "pipe"],
    });
    this.child = child;
    const started = new Promise<void>((resolve, reject) => {
      child.once("spawn", () => resolve());
      child.once("error", (error) => reject(error));
    });
    let buffer = "";
    child.stdout?.setEncoding("utf8");
    child.stdout?.on("data", (chunk: string) => {
      buffer += chunk;
      let cut: number;
      while ((cut = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, cut).replace(/\r$/, "");
        buffer = buffer.slice(cut + 1);
        if (!line.trim()) continue;
        let frame: JsonValue;
        try {
          frame = JSON.parse(line) as JsonValue;
        } catch {
          continue; // not a frame — the runtime never writes anything else here, but be safe
        }
        void this.onFrame?.(frame);
      }
    });
    child.stderr?.setEncoding("utf8");
    child.stderr?.on("data", (chunk: string) => {
      for (const line of chunk.split("\n")) {
        if (!line) continue;
        if (this.options.onStderr) this.options.onStderr(line);
        else process.stderr.write(`[shadow-hdk] ${line}\n`);
      }
    });
    child.once("exit", (code, signal) => {
      if (this.closing) return;
      this.onLost?.(`the runtime exited (${signal ?? `code ${code}`})`);
    });
    await started;
  }

  async send(frame: JsonValue): Promise<void> {
    const child = this.child;
    if (!child || !child.stdin || child.stdin.destroyed) throw new Error("the runtime is not running");
    await new Promise<void>((resolve, reject) => {
      child.stdin!.write(JSON.stringify(frame) + "\n", (error) => (error ? reject(error) : resolve()));
    });
  }

  /** End the runtime and its tree: close stdin (a served runtime ends on EOF), then SIGTERM, then
   *  SIGKILL after the grace. */
  close(): void {
    const child = this.child;
    if (!child) return;
    this.closing = true;
    try {
      child.stdin?.end();
    } catch {
      // already gone
    }
    const grace = (this.options.graceSeconds ?? 5) * 1000;
    const term = setTimeout(() => child.kill("SIGTERM"), 200);
    const kill = setTimeout(() => child.kill("SIGKILL"), grace);
    child.once("exit", () => {
      clearTimeout(term);
      clearTimeout(kill);
    });
  }
}

/** Start the runtime as a sidecar and hand back a connected client over its stdio. */
export async function spawnHarness(options: SpawnOptions): Promise<HarnessClient> {
  const client = new HarnessClient({ transport: new StdioTransport(options), onRequest: options.onRequest });
  await client.connect();
  return client;
}
