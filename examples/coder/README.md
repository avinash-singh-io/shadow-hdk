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
never touched the disk; `WorkspaceComponents` did, inside a root it cannot leave, and
`SubprocessSandbox` ran the code on a leash with a timeout and a capped output.

That is D42 in one screen: **it reasons, we govern.**

## Try breaking it

```bash
uv run python -m examples.coder ./my-workspace --confined
```

Now ask it to write a script *and run it*. It writes the file and cannot run it — and the shell
tools are not even in the list it was handed, because `RecordingServer` builds that list from
`visible()`, which is governed. A well-behaved agent never tries. One that asks anyway gets:

```
  ✕ refused: mode 'confined' does not permit this
```

The policy has never heard of `run_shell`. It refused **a set of effects** — something that writes
outside the workspace — which is why it would refuse a tool nobody has written yet, on exactly the
same grounds.

## What `building` actually grants, and why it says so

Running code is permitted in the default mode, and the banner tells you every time that on an
ordinary host **that reaches your whole machine, not just the workspace.**

That is not pessimism, it is arithmetic. `write_file` is genuinely confined — `WorkspaceComponents`
refuses a path that resolves outside its root, and refuses a hard link that reaches out of one. A
subprocess is not: it honours `cwd` and nothing else, so `cd ..` works and an absolute path works.

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
