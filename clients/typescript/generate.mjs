// Generate src/schemas/<Contract>.ts from ../../schemas/*.json with json-schema-to-typescript (D68).
//
// Deterministic: the contracts in index.json order, no timestamps, Prettier off — the output is a
// pure function of the schemas, which is what the invariant diffs against. One module per
// contract, because contracts share definitions (`Completed` is in Event, Item and Observation)
// and one file would declare each of them three times.
import { compile } from "json-schema-to-typescript";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
// Where the schemas are and where to write — overridable so the invariant can regenerate into a
// temp directory with the same code path and diff.
const schemas = process.env.SHADOW_HDK_SCHEMAS ?? join(here, "..", "..", "schemas");
const outDir = process.env.SHADOW_HDK_OUT ?? join(here, "src");
const target = join(outDir, "schemas");

// `discriminator` is OpenAPI's keyword, not JSON Schema's; pydantic writes it beside `oneOf` and
// json-schema-to-typescript's resolver does not know it. Every variant carries a `kind` const, so
// TypeScript narrows the union on `kind` with nothing lost.
function strip(node) {
  if (Array.isArray(node)) return node.map(strip);
  if (node && typeof node === "object") {
    const out = {};
    for (const [key, value] of Object.entries(node)) {
      if (key === "discriminator") continue;
      out[key] = strip(value);
    }
    return out;
  }
  return node;
}

// A recursive contract (`Item`, whose children are items) is published as `{ $defs, $ref }` —
// pydantic's shape. The resolver refuses a bare root `$ref`, so the target is inlined at the root
// and its self-references become `#`, which is what recursion looks like to it.
function rooted(schema, name) {
  if (!schema.$ref) return schema;
  const which = schema.$ref.split("/").pop();
  const defs = { ...schema.$defs };
  const root = defs[which];
  delete defs[which];
  const text = JSON.stringify({ ...root, $defs: defs, title: which }).replaceAll(
    JSON.stringify(`#/$defs/${which}`),
    JSON.stringify("#"),
  );
  return JSON.parse(text);
}

const index = JSON.parse(await readFile(join(schemas, "index.json"), "utf8"));
await mkdir(target, { recursive: true });
const banner = [
  "// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.",
  `// protocol_version ${index.protocol_version}. Regenerate with \`npm run generate\`; the invariant`,
  "// tests/invariants/test_the_typescript_client_is_current.py diffs these files.",
  "/* eslint-disable */",
  "",
].join("\n");
const barrel = [banner];
for (const name of index.contracts) {
  const schema = rooted(strip(JSON.parse(await readFile(join(schemas, `${name}.json`), "utf8"))), name);
  const ts = await compile(schema, name, {
    bannerComment: "",
    format: false,
    additionalProperties: false,
    unknownAny: true,
    declareExternallyReferenced: true,
  });
  const clean = ts.trimEnd().replace(/[ \t]+$/gm, "");
  await writeFile(join(target, `${name}.ts`), banner + clean + "\n", "utf8");
  barrel.push(`export type * as ${name}Schema from "./schemas/${name}.js";`);
}
barrel.push(`export const PROTOCOL_VERSION = ${JSON.stringify(index.protocol_version)};`);
await writeFile(join(outDir, "schemas.ts"), barrel.join("\n") + "\n", "utf8");
console.error(`wrote ${index.contracts.length} contracts under ${target} and ${join(outDir, "schemas.ts")}`);
