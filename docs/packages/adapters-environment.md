# `shadow_hdk.adapters.environment`

Where an agent's effects land, with a **mode** — `read-only`, `workspace-write`, `full` — enforced
once by the environment and true for every operation in it (D48).

`LocalEnvironment` confines with the operating system's own sandbox (seatbelt on macOS, bubblewrap
on Linux) and proves it at construction by what is denied (D36, D49). `SandboxEnvironment` consumes
an isolation platform somebody else built, with the root mounted in. Neither is built here; both are
governed here.
