// Tools as code, on this side of the wire (D21, ENH-031). A host writes a function; `tool()` makes
// it a `Registration` in the kit's published shape — an honest effect profile the mode judges, an
// interface from a JSON schema, a provenance that says whose it is — and `serveComponents` answers
// the runtime's two callbacks for it: `components.registrations` (what is here) and
// `components.invoke` (act). The runtime judges, admits and records the act exactly as it would a
// component in its own process; this side only runs the function.
import type { JsonValue } from "./client.js";
import type { Registration } from "./schemas/Registration.js";
import type { Observation } from "./schemas/Observation.js";

/** The effect vocabulary a tool declares — the same words a battery document uses (D70): scopes
 *  as lists of names or `"everything"`, the rest booleans. Omitted means the kit's default. */
export interface Effects {
  reads?: string[] | "everything";
  writes?: string[] | "everything";
  reaches?: boolean;
  reversible?: boolean;
  contained?: boolean;
  costs?: boolean;
}

export interface ToolOptions {
  description: string;
  effects: Effects;
  /** The input's JSON schema — what the model is shown and what arrives in `inputs`. */
  input?: { [key: string]: JsonValue };
  output?: { [key: string]: JsonValue };
  /** The interface's display name; defaults to the id. */
  name?: string;
  labels?: string[];
}

/** What a tool's function is told beside its inputs: the run and the step it acts inside. */
export interface Invocation {
  run_id: string;
  step: string;
}

export type ToolHandler<I = { [key: string]: JsonValue }> = (
  inputs: I,
  invocation: Invocation,
) => Promise<JsonValue | void> | JsonValue | void;

/** Throw this from a handler to refuse the act with a reason the record keeps — as distinct from
 *  failing, which is what any other thrown error becomes. */
export class Refusal extends Error {
  constructor(public readonly reason: string) {
    super(reason);
    this.name = "Refusal";
  }
}

export interface Tool {
  registration: Registration;
  handler: ToolHandler;
}

function scopes(given: string[] | "everything" | undefined): { names: string[]; everything: boolean } | undefined {
  if (given === undefined) return undefined;
  if (given === "everything") return { names: [], everything: true };
  return { names: [...given], everything: false };
}

/** A function, made a component in the kit's published shape. */
export function tool<I = { [key: string]: JsonValue }>(id: string, options: ToolOptions, handler: ToolHandler<I>): Tool {
  const effects: Registration["component"]["effects"] = {};
  const reads = scopes(options.effects.reads);
  const writes = scopes(options.effects.writes);
  if (reads) effects.reads = reads;
  if (writes) effects.writes = writes;
  if (options.effects.reaches !== undefined) effects.reaches = options.effects.reaches;
  if (options.effects.reversible !== undefined) effects.reversible = options.effects.reversible;
  if (options.effects.contained !== undefined) effects.contained = options.effects.contained;
  if (options.effects.costs !== undefined) effects.costs = options.effects.costs;
  const registration: Registration = {
    id,
    component: {
      interface: {
        name: options.name ?? id,
        description: options.description,
        ...(options.input ? { input_schema: options.input } : {}),
        ...(options.output ? { output_schema: options.output } : {}),
      },
      effects,
      provenance: {
        adapter: "typescript",
        at: new Date().toISOString(),
        registered_by: "host",
      },
      ...(options.labels ? { labels: options.labels } : {}),
    },
  };
  return { registration, handler: handler as ToolHandler };
}

/** The two callbacks, answered from a list of tools. Returns the handler map the client installs. */
export function serveComponents(tools: Tool[]): Map<string, (params: JsonValue) => Promise<JsonValue>> {
  const byId = new Map(tools.map((t) => [t.registration.id, t]));
  const handlers = new Map<string, (params: JsonValue) => Promise<JsonValue>>();
  handlers.set("components.registrations", async () => tools.map((t) => t.registration as unknown as JsonValue));
  handlers.set("components.invoke", async (params) => {
    const p = (params ?? {}) as { registration?: string; inputs?: JsonValue; run_id?: string; step?: string };
    const found = byId.get(String(p.registration));
    let observation: Observation;
    if (!found) {
      observation = { kind: "failed", error: `no tool ${String(p.registration)} on this host` };
    } else {
      try {
        const output = await found.handler((p.inputs ?? {}) as { [key: string]: JsonValue }, {
          run_id: String(p.run_id ?? ""),
          step: String(p.step ?? ""),
        });
        observation = { kind: "completed", output: (output ?? {}) as { [k: string]: unknown } };
      } catch (error) {
        observation =
          error instanceof Refusal
            ? { kind: "refused", reason: error.reason }
            : { kind: "failed", error: error instanceof Error ? `${error.name}: ${error.message}` : String(error) };
      }
    }
    return observation as unknown as JsonValue;
  });
  return handlers;
}
