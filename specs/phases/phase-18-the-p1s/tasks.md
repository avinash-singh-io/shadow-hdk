---
type: Tasks
phase: 18-the-p1s
---

# Phase 18 — tasks

## Group 1 — the workspace and the leash
- [x] reproduce: hard-link read **and overwrite**; a NUL byte raising out of `invoke`; a marker written after the step returned; `HOME` in the child
- [x] `_resolve` refuses a regular file more than one name reaches (directories exempt: their link count is their subdirectories plus two); `ValueError` from a NUL byte caught where every other filesystem refusal already was; `adapters.md` corrected on `write_file`'s `contained`
- [x] `run_leashed`: own session, the **group** killed when the leash returns (D35), no `HOME`, `TMPDIR` in the workspace, `memory_mb` by `prlimit` from the parent with `MEMORY_LIMIT_ENFORCED` saying where it bites, output capped as it arrives
- [x] RED: the four, the other way round — 24 tests (9 workspace, 15 leash, one skipped on macOS with its reason)
- [x] Gate — ruff 0 / format 0 / mypy 0 (121 files) / pytest 752 passed, 1 skipped, 10 deselected; 15 mutations, all bite

## Group 2 — a proof is a capability test (D36)
- [x] reproduce: a five-line fake `runsc` on `PATH` produced a `Proof`
- [x] `Proof.checks` (what was attempted and denied) and `Proof.declared` (the backend's own word, a claim); `prove()` in the **sandbox** so no backend judges itself; `Inconclusive` distinct from a denial; `trusting_the_backend_without_proof` named for the sentence it signs
- [x] the backends moved from `probe()` to `declares()`; the live gVisor and Firecracker tests still skip, now reading the new shape
- [x] RED: a box that does not box cannot prove; a banner is not a proof; an inconclusive check is not a denial; trust covers an unknown and **not** a fact; the probe goes through `wrap`; the proof carries its evidence — 12 tests, plus the six existing ones moved over
- [x] Gate — ruff 0 / format 0 / mypy 0 (122 files) / pytest 764 passed, 1 skipped, 10 deselected; 12 mutations, all bite

## Groups 3–5
- [x] BUG-015 — a held child across its parent's park (**D37**, contract 0.10.0 → 0.11.0)
  - [x] `RunState.children` carries handle, run id, composition and ceiling; a released handle stays as a `None` headstone so a `FanOut`'s branches merge the same in any order
  - [x] a child shares its parent's checkpointer by default — a private in-memory saver could never have outlived the parent's park
  - [x] one spawned with a checkpointer of its own is named in `children.lost` with the reason, never silently replaced
  - [x] RED: the same handle either side of the park; a restored child answers a `send` where it slept; an unreachable one is reported; a released one and one that *ended on a send* both stay gone — 7 tests
  - [x] Gate — ruff 0 / format 0 / mypy 0 (123 files) / pytest 771 passed, 1 skipped, 10 deselected; 14 mutations, 13 bite, 1 named equivalent
- [x] BUG-010 — a parked step resumes where it parked (**D38**, contract 0.11.0 → 0.12.0)
  - [x] reproduce, all four: an `Await` called its component twice and emitted `Invoked` twice; a re-run `Refuse` overrode the host's `Allow`; a re-run `Allow` discarded the host's `Refuse` **and ran the work**; two Asks in one `FanOut` took one resume each and re-ran the answered branch
  - [x] **the audit's row was wrong on the fourth** — no `failed`, no LangGraph message; it parks again. Corrected in the backlog rather than quietly closed
  - [x] `_stream` passes the checkpoint's pending interrupts down to `StepExecutor`; a step that parked is not judged again and an `Await` is not invoked again — it resumes at its interrupt
  - [x] an `Ask` is answered with a `Judgement`: an object in process, its JSON over the wire loaded at the runtime's edge (D19); a bare value is refused, not read as consent
  - [x] one answer settles every step that asked (what a fan-out needs); an answer keyed by step id addresses them one at a time
  - [x] D33's `resume_seq` and D37's records both ride this path and still hold — each has a test either side of the park
  - [x] five existing tests changed because they encoded the old behaviour, one with a docstring calling the double act a feature
  - [x] RED: 8 tests, including a resume inside an `Until` loop that must happen once, not every iteration
  - [x] Gate — ruff 0 / format 0 / mypy 0 (124 files) / pytest 779 passed, 1 skipped, 10 deselected; 12 mutations, all bite
- [ ] BUG-011, BUG-012, TD-003
- [ ] TD-009 — the workflow change, and the pull request prepared for the owner
- [ ] records, board, status, roadmap
