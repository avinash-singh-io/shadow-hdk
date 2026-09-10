"""A coding agent you can talk to, whose every action this runtime governs.

Your subscription pays for the thinking. **Our tools do the acting**, and that is the whole point:

* the model is Claude Code, driven through its own line-delimited JSON mode, using the subscription
  already on this machine — no API key, and no credential this program ever sees;
* its native file and shell tools are **refused**, and the run's own registry is handed to it
  instead, so a file it writes goes through `WorkspaceComponents` and a command it runs goes through
  `SubprocessSandbox`;
* every one of those calls arrives as a step on our graph — judged on its effects by the governance
  port, charged to the lease, and on the event stream;
* nothing is written anywhere this program did not choose, because the runtime has no write path.

Which is D42 in one paragraph: **it reasons, we govern.**

Run it:

    uv run python -m examples.coder

Then talk to it. Ask it to write a script and run it.
"""
