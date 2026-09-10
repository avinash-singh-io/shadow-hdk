---
type: Guide
---

# Six views of shadow-hdk

**Each page explains itself.** Every diagram carries a one-line subtitle, five numbered chapters
that walk it a box at a time, and cards naming what each box is and what the drawing means. Open
one and read it; there is no companion document to fetch.

| The question it answers | Kind | Open |
|---|---|---|
| What are the pieces, and which way do dependencies point? | architecture | `harness.architecture.html` |
| How does somebody actually use this? | architecture | `consuming.architecture.html` |
| What happens, in order, during one run? | sequence | `a-run.sequence.html` |
| What decides whether a step may run, and what does each answer produce? | workflow | `governed-step.workflow.html` |
| What states can a run be in, and how does it survive a process? | lifecycle | `run.lifecycle.html` |
| What becomes what, from a brief to the record? | dataflow | `plan-to-record.dataflow.html` |

Start with `harness.architecture`. It carries the component glossary, the adapter list and the
counted vocabulary, and each of its boxes links to the file that implements it.

## Reading any one of them

- **The chapters** in the header walk the diagram in order. Press play, or step through them.
- **Focus a box** to open its passport: what it is, what connects to it, and — on the architecture
  page — the verified source file behind it.
- **The cards** below the drawing name every box and state the rules the drawing encodes.
- Themes, pan and zoom, search, relationship tracing and export are all in the page.

## Why six and not one

Each answers something the others structurally cannot. The architecture has no time in it, so it
cannot show that governance is asked before a component runs. The sequence shows that order but
only one path. The workflow shows the branches but nothing between steps. The lifecycle covers
that, and carries no content at all. The dataflow carries only content and no control. And none of
them says how you would call any of it, which is the sixth.

## Regenerating

The Archify skill lives at `~/.claude/skills/archify`. From that directory:

```bash
node bin/archify.mjs deliver architecture <spec>.json <out>.html --quality showcase --json
```

The architecture page also needs `--repo-root` pointing at this repository, because its source
references are verified against a pinned revision at build time.

Every page passed that showcase gate with zero composition errors and zero warnings. Automated
browser evidence is **skipped**: `visual-check` needs Chrome or Chromium, which is not installed
here. Each page was instead opened and read at desktop sizes by hand.

The MQTT adapter — one adapter among fourteen, and deliberately the most replaceable part — has its
own diagrams under `specs/phases/phase-16-mqtt/diagrams/`.
