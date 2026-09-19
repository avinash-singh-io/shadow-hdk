# `shadow_hdk.adapters.environment`

Where an agent's effects land, with a **mode** — `read-only`, `workspace-write`, `full` — enforced
once by the environment and true for every operation in it (D48).

`LocalEnvironment` confines with the operating system's own mechanism and proves it at construction
by what is denied (D36, D49): seatbelt on macOS; on Linux the kit's `shadow-hdk-linux-sandbox`
helper — Landlock and seccomp applied to itself before `exec`, installed with the kit on x86_64 and
aarch64 — with bubblewrap behind it (Epic 0010, D133). A machine's candidates are tried in that
order and **the proof decides** which is in force; `Isolation.mechanism` names it on the evidence
(`landlock confines writes`). `SandboxEnvironment` consumes an isolation platform somebody else
built, with the root mounted in. Neither is built here; both are governed here.

- `local_sandboxes()` — the candidates in order; `local_sandbox()` the first or `None`.
- `SHADOW_HDK_SANDBOX=landlock|bubblewrap|seatbelt` narrows the candidates to one;
  `SHADOW_HDK_LINUX_SANDBOX` names the helper's path when it is neither beside the interpreter nor
  on `PATH`.
- A confined mode is refused (`CannotEnforce`) naming each mechanism the proof rejected and what it
  did not see, or — where there is none — the three the kit knows and what would install them.
  `full` always constructs.
