# Optional workbench components

Products choose the packs they need. `shadow-hdk[workbench]` includes local listener inspection
with psutil and entity-free JUnit parsing with defusedxml. Ordinary installation does not start a
command, inspect a process, launch a browser or download its binary.

```python
from shadow_hdk.adapters.workbench import HostDoor, LocalProcessListeners, WorkbenchComponents

# `environment` is the host's existing environment for this working copy.
door = HostDoor(environment, listeners=LocalProcessListeners())
pack = WorkbenchComponents(door)
```

Include `pack` in `Ports.components` when agents should receive `list_jobs`, `read_job` and
`test_results`. The existing command pack supplies `run_background` and `kill_job`. These are
ordinary components: the registry narrows their offered set, governance judges their declared
effects, and invocation/results reach the act record. The workbench pack's operations declare
reads according to the environment's actual isolation and mode.

The person's door calls the same environment directly, with no model or agent:

```python
started = await door.background("python -m http.server 8000")
jobs = await door.jobs()
output = await door.output(job_id, cursor=0, limit=64000)
await door.stop(job_id)
await door.run("git status --short")
content = await door.read("src/app.py")
results = await door.results("test-results.xml")
```

The host authenticates the person and supplies their environment policy. A door does not grant
authority or close a shared environment. Its owner closes the environment; jobs survive agent
turns until stopped or that owner closes them. Commands are noninteractive; PTY sessions are
not part of this release.

Each output reader supplies its own absolute **character** cursor. Responses carry `start`,
`cursor`, `output`, `truncated` and `more`, plus job/command/PID/running/exit-code metadata.
The bounded buffer explicitly reports dropped output. Polling through this door or `read_job`
never advances the agent's legacy `job_output` cursor. An exit code is unknown while running.
Stopping also ends owned descendants after the process leader exits and settles the output
readers. Job IDs are scoped to their environment; another environment's ID is refused.

Output URLs are hints with `source: output, verified: false`. For a local environment, optional
`LocalProcessListeners` verifies bound host/port pairs for owned processes and descendants.
It reports TCP listeners without guessing HTTP versus HTTPS. Inspection failures are visible
in `inspection_error`; a remote environment supplies its own listener port instead of asking
this computer to inspect remote PIDs. The host chooses which address to display or open.

`test_results` reads a report through the same file door and parses JUnit XML up to 8 MB. Counts
come from testcase records, including nested suites. Data includes passed/failed/skipped counts,
failing names, failure/error messages and output, skip reasons, and case/suite stdout/stderr.
Declared test counts must match the cases present. Malformed or incomplete reports and XML
entities are refused; console prose is never treated as measured test results. A runner should
write a JUnit report (for pytest, `--junitxml=test-results.xml`) and only publish that report after
the run has finished. File roots and confinement remain the environment's responsibility.
