---
type: Tasks
phase: 22
---

# Tasks — Phase 22, The environment

## Group 1 — the concept
- [x] `Mode`, `Isolation`, `effects_of` — the one derivation, tested on every (mode, operation) cell
- [x] `Environment` base: five operations registered with derived profiles
- [x] a write in `read-only` is `Refused` naming the mode, before governance is asked
- [x] `CannotEnforce` at construction when a mode cannot be made true

## Group 2 — local
- [x] seatbelt profile from (mode, root); bubblewrap argv from the same
- [x] proven at construction: write-outside denied, socket denied, write-inside allowed
- [x] the declared `Isolation` is what the proof found
- [x] every operation through the leash inside the box; timeout and output cap hold
- [x] neither sandbox present + confined mode → `CannotEnforce` naming the fix
- [x] `full` always constructs and declares everything

## Group 3 — isolated
- [x] `Box` on the backend seam; `SandboxEnvironment` over it
- [x] `OpenSandboxBackend` — create with the root mounted, run, read, write, close
- [x] `prove()` denies a write outside the mount as well as a socket
- [x] the live proof skips without a server, saying so; a fake `Box` proves the translation
- [x] E2B / Daytona: recorded as the next file (D50) — not built this phase

## Group 4 — migration
- [x] the coder example on `LocalEnvironment`; `--mode`
- [x] the three adapters' tests moved or shown redundant
- [x] `workspace`, `sandbox_subprocess`, `contained` deleted everywhere they were named
- [x] `ENFORCED_BY` and `CONTRACTED` true again
- [x] 0.16.0 everywhere; `EXPECTED` and its reason

## Close
- [x] D48–D50; index
- [x] a live turn inside the environment
- [x] README, file-structure, adapters.md
- [x] status, roadmap, changelog, board — *audit 2026-09-20: the 0.22.0 rows exist in all four; the box lagged*
