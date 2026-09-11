---
type: Plan
phase: 22
---

# Plan — Phase 22, The environment

## Group 1 — the concept (runtime)

`packages/runtime/src/shadow_hdk/runtime/environment.py` — below every adapter, the way the
leash and the device contract are, so a second environment never imports the first:

- `Mode = Literal["read-only", "workspace-write", "full"]`.
- `Isolation` — what is **true** of an environment: `writes_confined`, `reads_confined`,
  `network_denied`, `proven`. Never declared by a wrapper; established by a proof or by an honest
  *no*.
- `effects_of(isolation, mode, operation)` — the one derivation. `read` under `read-only` with
  reads confined is `{workspace}`; `write` under `read-only` is refused before it is judged;
  `run` under `full` is everything.
- `Environment(ComponentPort)` — the abstract shape: `read_file`, `write_file`, `list_dir`,
  `run_shell`, `run_python`, each registered with the derived profile; subclasses supply the
  mechanism. A write in `read-only` is a `Refused` observation with the mode named.
- `CannotEnforce` — raised at construction when a mode cannot be made true.

## Group 2 — `LocalEnvironment` (adapter `environment`)

- macOS: a seatbelt profile from mode and root — `(deny file-write*)` for read-only; `(allow
  file-write* (subpath root))` for workspace-write; `(deny network*)` for both; nothing for full.
- Linux: bubblewrap with `--ro-bind /` and `--bind root root`, `--unshare-net`, when `bwrap` is
  present.
- Neither present and a confined mode asked: `CannotEnforce`, naming what would fix it.
- **Proven at construction (D36)**: a write outside the root is attempted and must fail; a socket
  is attempted and must fail; a write inside must succeed. The declared `Isolation` is what the
  proof found, never what the profile says.
- Every operation runs through the runtime's leash (`run_leashed`, `start_leashed`) wrapped in the
  sandbox argv — so a command is confined *and* on a timeout with a capped output.
- File operations go through the same wrapper: a read is `cat` inside the box, a write is a
  redirect inside the box. One mechanism, every operation.

## Group 3 — `SandboxEnvironment` and the OpenSandbox backend

- `IsolationBackend` grows what a remote box needs: `open(root, mode) -> Box`, where a `Box`
  runs a command, reads and writes a file, and closes. The old `wrap(argv)` shape stays for local
  wrappers.
- `OpenSandboxBackend`: `Sandbox.create(image, volumes=[Volume(host=root, mount_path=…,
  read_only=mode == "read-only")], network_policy=deny)`; `commands.run`; `files`.
- `prove()` extended: a write outside the mount must be denied, not only a socket.
- Its live proof needs a server and Docker — **skips** here and says why; a fake `Box` proves the
  translation.
- E2B and Daytona: the same `Box` shape, each an adapter, if time allows — else recorded as the
  next file.

## Group 4 — migration, and the three deleted

- The coder example uses `LocalEnvironment(root, mode)`; `--confined` becomes `--mode`.
- Every test the three adapters had is either moved onto the environment or shown redundant.
- `workspace`, `sandbox_subprocess`, `contained` deleted; their pyproject entries, workspace
  members, mypy paths, ruff src, the invariant tables (`CONTRACTED`, `ENFORCED_BY`), the
  documents, the README.
- Contract change (a new runtime type crosses as a registration's effects; `Isolation` on the
  record) → 0.16.0.

## Close

D48–D50 in history; index regenerated; the example runs inside an environment on a live turn;
status, roadmap, changelog, board.
