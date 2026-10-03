---
type: Handoff
to: the Codex lane
date: 2026-10-04
---

# Handoff prompt — paste the block below into a fresh Codex session

Everything it refers to is in the repositories. Nothing depends on a conversation.

---

```
You are picking up HDK and Shadow work in the shadow-workspace. Read before acting.

ORIENT
  cd /Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk
  cat specs/status.md                                  # Rule 1, always first
  cat specs/handoffs/2026-10-03-to-the-codex-lane.md   # your cold-start brief
  cat ../shadow-ecosystem/initiatives/0002-generic-before-product.md
  uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q

Branch `phase-66-the-short-list` is current, pushed and clean, and already
contains the 0.44.1 patch release. `main` is v0.44.1, published.

WHAT WAS JUST DECIDED, and why it changes the work

  An audit measured shadow-hdk's runtime layer: it defines FIFTEEN operations by
  name — read_file, write_file, edit_file, apply_patch, move_file, glob, grep,
  run_shell, run_python, run_background, job_output, kill_job, checkpoint,
  restore, list_checkpoints — in the layer whose own boundary rule says a tool
  name's meaning belongs behind a port. None passes the test the product's own
  audit stated: a support desk does not need worktrees.

  So D184's parity list is NOT a list of capabilities Shadow lacks. It is a list
  of things HDK should not have had in that layer. Do not port them.

  Four decisions, in ../shadow-ecosystem/initiatives/0002-generic-before-product.md:
    D-M  the file-and-shell tools are COMPONENTS published as a PACK, loaded only
         when a run asks. Not Core, not Runtime, never mandatory. Shadow's phase
         64 G11 tool preset is already that shape. H27, H28 and the terminal half
         of H18 join that pack.
    D-N  BUILD the Proposal port in Shadow: propose(Proposal{kind, payload,
         provenance, grounds}), outbound, retention none, never journaled. An
         opaque kind is what makes it mechanism rather than content. Without it,
         Shadow phase 55 journals a compaction and phase 59 journals minted
         skills — the harness persisting product artifacts it cannot interpret.
    D-O  the genericity test is now enforceable, recorded as shadow-hdk D190 in
         specs/project-rules.md: a kernel or runtime addition must name the
         property of ANY agent product that needs it, and a tool name in those
         layers is a review failure. The sentence to look for is "a coding tool,
         a support desk and a research assistant would each use this".
    D-P  a capability that needs the outside world is a PORT plus an OPTIONAL
         ADAPTER, not one thing. H24 (browser) and H25 (page fetch).

YOUR WORK, in order

  1. shadow-hdk, finish 0.45: E (skill on the agent row), C (plan on the row),
     D (description on the row), then H6, H7, H8 — each CONFIRMED against the
     source and reported BEFORE it is built. The approved design for E, C and D
     is in specs/phases/phase-66-the-short-list/evidence/g2-h11-gaps.md; build
     it, do not redesign it. Do NOT add absorb or offload_over by symmetry.
     Every addition must pass D190, and say so in its commit.

  2. Release as a TRAIN, one item per release, not a batch. D9 says a contract
     change is a MINOR bump pre-1.0, so the numbers are 0.45.0, 0.46.0, 0.47.0 —
     not 0.45.1. The DDL-free default flip lands in the first 0.45 release, as a
     named behaviour change in its note. A note in specs/epics/ for every release:
     that file is the only channel to lane P, who reads it from git.

  3. Update specs/planning/what-moves-to-shadow.md before closing anything. D184
     makes that a standing requirement, and it has a row that says explicitly
     that whoever builds E, C and D updates it.

RULES THAT ARE NOT NEGOTIABLE
  - HDK is maintenance only: bugs and the product's pins. Nothing new.
  - Build nothing from H12–H17, H21, H22, H29, H30, H41–H43. Those are Shadow's.
  - TDD strict, and mutation-check every assertion with scripts/mutate-one.py.
    BITES is good; SURVIVED means the assertion does not bite — and if the mutant
    is equivalent, delete the code rather than invent a test that cannot tell.
  - Protected pushes are the owner's. Prepare everything, verify the merged trees
    match the gated one, then hand over the commands.

TRAPS, each of which cost real time here
  - A failing test that stands up a ServeHost HANGS instead of failing (TD-019).
    Extract the decision into a pure function and check that.
  - A wall-clock margin is something a loaded machine can eat (TD-018, five
    instances). Where a property is countable, COUNT it.
  - Growing a port must break no adapter (D14). Read a new element where offered,
    default it where not.
  - THE RECURRING DEFECT HERE is a field accepted by a signature and read by
    nothing — BUG-230, BUG-231, BUG-236, and once inside BUG-237's own fix with
    nine tests green. Prove the BEHAVIOUR changes. For anything published, assert
    against the INSTALLED artifact.
  - Never read pytest through `tail` — it swallows the exit code. Redirect to a
    file and read both.
  - Backticks in `git commit -m` are shell-expanded. Use `-F` with a file.
  - After editing a file with a script, GREP TO VERIFY before committing. An
    append here reported success and silently did not persist, because a later
    edit in the same turn read a stale copy.
  - Three invariants will catch you: a D-number must be in
    specs/decisions/index.md AND stated in the document it points at; a new
    public Thread property must be accounted for in the wire-parity test; and any
    path-shaped string in a document must name a file that exists.

OPEN, AND NOT YOURS TO DECIDE
  - TD-020 / H37: Codex's instruction fold is unmeasured; needs an account where
    Codex accepts a model.
  - TD-018's fifth instance has a known fix shape in adapters/mqtt/link.py and
    wants its own quick-task.
  - The ten genuinely generic audit items (H19, H31–H36, H38–H40) have no home in
    either repo. That is the real framework backlog and the owner has not placed it.
```

---

## For the owner, not the prompt

Three things the prompt deliberately does not decide:

1. **Shadow's own architecture document** should carry the pack framing explicitly. That file belongs
   to `shadow`, so it is not edited from here — initiative 0002 names it as Shadow's contribution.
2. **The ten generic unplaced items** are the remaining framework backlog. They are listed in the
   initiative; nobody owns them.
3. **D189's rationale** is still recorded as this repository's reading rather than the owner's words.
