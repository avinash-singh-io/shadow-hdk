# shadow-hdk-adapters-sandbox-subprocess

Runs `run_python` and `run_shell` inside a workspace, with a timeout and an output cap.

**It is a leash, not a boundary.** `contained` is a constructor argument with no default, because a
sandbox that claimed containment it did not have would be the most dangerous lie in this system. On
an uncontained host `reaches` is forced to `True`: we cannot stop a subprocess opening a socket, so
we do not say we can. Real isolation is Phase 11 — gVisor and Firecracker.
