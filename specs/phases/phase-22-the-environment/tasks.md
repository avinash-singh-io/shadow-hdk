---
type: Tasks
phase: 22
---

# Tasks — Phase 22, The environment

## Group 1 — the concept
- [ ] `Mode`, `Isolation`, `effects_of` — the one derivation, tested on every (mode, operation) cell
- [ ] `Environment` base: five operations registered with derived profiles
- [ ] a write in `read-only` is `Refused` naming the mode, before governance is asked
- [ ] `CannotEnforce` at construction when a mode cannot be made true

## Group 2 — local
- [ ] seatbelt profile from (mode, root); bubblewrap argv from the same
- [ ] proven at construction: write-outside denied, socket denied, write-inside allowed
- [ ] the declared `Isolation` is what the proof found
- [ ] every operation through the leash inside the box; timeout and output cap hold
- [ ] neither sandbox present + confined mode → `CannotEnforce` naming the fix
- [ ] `full` always constructs and declares everything

## Group 3 — isolated
- [ ] `Box` on the backend seam; `SandboxEnvironment` over it
- [ ] `OpenSandboxBackend` — create with the root mounted, run, read, write, close
- [ ] `prove()` denies a write outside the mount as well as a socket
- [ ] the live proof skips without a server, saying so; a fake `Box` proves the translation
- [ ] E2B / Daytona: recorded as the next file, or built

## Group 4 — migration
- [ ] the coder example on `LocalEnvironment`; `--mode`
- [ ] the three adapters' tests moved or shown redundant
- [ ] `workspace`, `sandbox_subprocess`, `contained` deleted everywhere they were named
- [ ] `ENFORCED_BY` and `CONTRACTED` true again
- [ ] 0.16.0 everywhere; `EXPECTED` and its reason

## Close
- [ ] D48–D50; index
- [ ] a live turn inside the environment
- [ ] README, file-structure, adapters.md
- [ ] status, roadmap, changelog, board
