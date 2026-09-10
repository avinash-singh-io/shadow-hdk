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

Open [`workshop.py`](workshop.py) and swap `BUILDING` for `LOOKING` in `workshop()`. Ask it to write
a file again. You get:

```
  ✕ refused: mode 'looking' does not permit this
```

The policy has never heard of `write_file`. It refused a **set of effects** — something that writes
the workspace and is not reversible — which is why the same rule governs a tool nobody has written
yet, and why the agent cannot get around it by picking a differently-named tool.

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
