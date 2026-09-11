# `examples/coder` — a coding agent whose every action this runtime governs

```bash
uv run python -m examples.coder ./my-workspace
```

Then talk to it. *"Write a script that prints the first 20 primes and run it."*

## What this is actually demonstrating

Your **subscription** pays for the thinking. **Our tools** do the acting.

The provider is Claude Code, driven through its own line-delimited JSON mode using the subscription
already on this machine. No API key. No credential this program ever reads.

Its own file and shell tools are **refused** at launch, and the run's registry is handed to it
instead. So when it decides to write a file, this happens:

```
  · write_file
    → Completed(output={'path': 'hello.py', 'bytes': 12})
  · run_shell
    → Completed(output={'exit_code': 0, 'stdout': 'hi\n', 'truncated': False})
```

Those are **steps on our graph** — child runs of the conversation, each one judged on its effects by
the governance port before it happened, charged to the lease, and on the event stream. The agent
never touched the disk; the `LocalEnvironment` did — inside a root the OS sandbox will not let a
command leave, on a leash with a timeout and a capped output.

That is D42 in one screen: **it reasons, we govern.**

## The mode is the whole example

```bash
uv run python -m examples.coder ./my-workspace                          # workspace-write
uv run python -m examples.coder ./my-workspace --mode=read-only
uv run python -m examples.coder ./my-workspace --mode=full
```

There is **one environment with a mode** (D48), and the confinement is the operating system's,
not a comment's. In `workspace-write` — the default — every command the agent runs is inside the
OS sandbox (`sandbox-exec` on macOS, bubblewrap on Linux): a write outside this directory is
*Operation not permitted*, a socket is denied, and both were **proven before the environment
existed** by trying them and watching them fail (D49). What the environment declares to the policy
is what that proof found.

Ask it, in `workspace-write`, to write a script that touches your home directory and run it. The
script runs; the write fails at the operating system; the record shows the command and its
non-zero exit. Ask the same in `read-only` and the shell tools are not even in the list it was
handed — `RecordingServer` builds that list from `visible()`, which is governed — and a write is
refused by the environment itself before any policy is consulted:

```
  ✕ refused: this environment is read-only; a write is not offered
```

## What `full` actually grants, and why it says so

`--mode=full` is an ordinary subprocess on an ordinary host, and the banner tells you every time
that **it reaches your whole machine, not just the workspace.** The environment declares
`writes: everything` for it, because that is the truth, and the `open` policy admits it out loud.

On a machine with no OS sandbox, `workspace-write` **refuses to start** rather than quietly
becoming `full`:

```
mode 'workspace-write' needs writes confined to the root, the network denied, and a proven
denial (D36) rather than a claim, and this environment cannot provide it — this machine has no
OS sandbox (sandbox-exec on macOS, bwrap on Linux)
```

This was wrong until BUG-018, and the example is how it was found. Asked to build a landing page,
the agent ran `ls` and `cat` and came back with this repository's `specs/status.md`, a listing of the
parent directory, files from unrelated projects, and `/Applications`. Nothing refused it, because
the sandbox had declared `reads: {workspace}` — a claim that was false, and that governance had no
way to check.

The profile is honest now, so a mode that permits running code has to say `everything`, and reading
that in [`workshop.py`](workshop.py) is meant to be uncomfortable. Narrowing it back is exactly what
a **contained** sandbox is for (D25, D36) — and why those proofs need a Linux host rather than a
laptop.

## What it needs

A provider that is installed and signed in. The example asks and tells you:

```
no provider on this machine is ready:
  Claude Code   not-signed-in  install Claude Code, then `claude auth login`
  OpenCode      absent         brew install sst/tap/opencode
```

It never installs anything and never reads a credential — it asks each CLI about itself and
believes the answer, or says it could not tell.

## The files

| | |
|---|---|
| [`workshop.py`](workshop.py) | the tools, the policy, the lease — everything a host decides, and it is short on purpose |
| [`session.py`](session.py) | the wiring: a run, a registry served on a loopback socket, a provider that can only reach it |
| [`__main__.py`](__main__.py) | the conversation |
