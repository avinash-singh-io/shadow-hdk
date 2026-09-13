"""What a provider is: a binary, some probes, some environment rules, a transport (D40).

A provider is **data**, and it lives in the kernel for the same reason `EffectProfile` does — it is
a fact with no I/O in it. The code that resolves, probes and launches one lives above; nothing here
runs anything.

**Why data and not a class per provider.** D17 made agent architectures TOML a team writes without
touching Python, and a provider is the same kind of fact. The test is whether the *second* provider
costs a file or a phase. The reference implementation this is taken from keeps its provider record
as data and then leaks two things back into per-provider code — the spawn environment as a
hand-written branch per agent, and authentication classified by a per-agent function matching
English error text. Both are fields here.

**Every default is the conservative one**, the rule `EffectProfile` set with `ASSUME_WORST`: a
record that omitted a field must never read as a permission. No auth probe does not mean *signed
in*; it means nobody asked. No `injects_tools` does not mean *takes our tools*; it means it has not
said so, and D42's socket cannot be closed around it.

**`transport` and `injects_tools` are open strings, not enumerations.** Making them `Literal` would
mean the kernel's contract changes every time somebody teaches this runtime a new protocol, which is
the cost D22 refused for ports and this refuses for the same reason. An adapter declares which
transports it serves; an unknown one is refused by whoever was asked to open it, naming the string.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ProviderKind = Literal["model", "agent"]
"""The two seams (D39). *model* sells inference and the caller owns the loop; *agent* sells agency
and owns its own. There is no third, because a thing that is neither is not a provider."""

ProviderStatus = Literal["ready", "absent", "not-signed-in", "too-old", "unknown"]
"""What asking a provider about itself can honestly return.

`unknown` is the one that matters and the one a two-state design gets wrong. Some CLIs cannot be
asked — they have no status command, or they answer in prose nothing here can classify. Reporting
*not signed in* because we could not tell sends somebody to fix what is not broken, so the fifth
answer exists to be given.
"""


@dataclass(frozen=True)
class EnvVar:
    """One name and one value, for the environment a provider is launched with."""

    name: str
    value: str


@dataclass(frozen=True)
class Behaviour:
    """Who the model should be for a mode (D64): a role, a model, an effort, a temperature, and
    which of the run's tools it is offered. Data, mapped to a CLI's flags by
    `Dialect.behaviour_args` — a product authors a mode with a behaviour, not launch args.

    Every field optional: an unset field changes nothing, so a mode carries only what it means to
    change. `tools_offered` is empty for *all of the run's* (the default); a tuple names a subset.
    """

    system: str = ""
    append_system: str = ""
    model: str = ""
    effort: str = ""
    temperature: float | None = None
    tools_offered: tuple[str, ...] = ()


@dataclass(frozen=True)
class BehaviourArg:
    """One behaviour field, and the flag the CLI takes it as (D64)."""

    field: str
    flag: str


@dataclass(frozen=True)
class Delta:
    """One kind of streamed piece a CLI emits (D63): which value of the delta-kind field it is,
    what activity kind it becomes, and where its text sits in the event."""

    on: str
    kind: str
    at: str


@dataclass(frozen=True)
class Dialect:
    """How to read one CLI's line-delimited JSON event stream (D40).

    Claude Code and Codex both answer on stdout as newline-delimited JSON. They disagree about every
    *name* — which key holds the event type, which type carries assistant text, where the text sits,
    what ends a turn — and about nothing else. The shape is shared; only the names differ. So the
    names are data.

    **This is not a query language and must not become one.** Ten fields, each a literal event name
    or a dotted path where `[]` means *each element of this list*. No expressions, no conditionals,
    no arithmetic. A CLI whose stream does not fit gets code — the same cut the reference makes with
    its `streamFormat` enum, except these are fields where those are hand-written parsers.

    Every default is the conservative one. A dialect that named no event reads nothing rather than
    matching something by accident: a stream nobody described is a stream nobody can read, and
    saying so is better than inventing a reading of it.
    """

    resident: bool = False
    """Whether one process serves the whole conversation, or one process serves one turn.

    Claude Code with `--input-format stream-json` keeps reading stdin, so the conversation is one
    process and its own memory carries the history. `codex exec` is the other shape: a turn per
    process, with the CLI's own resume flag threading them together. Both are facts about that CLI,
    so both are fields.
    """

    resume_args: tuple[str, ...] = ()
    """What a non-resident CLI is given to continue its previous session, with the session id
    appended. Empty means each turn starts cold."""

    session_id_at: str = ""
    """Where a non-resident CLI reports the session id a later turn resumes from."""

    prompt_shape: str = "text"
    """How a turn is written to the child. `text` is the words on stdin; a CLI wanting an envelope
    names its own. A fact about that CLI, not about this runtime."""

    type_key: str = "type"
    """Which key on each line says what kind of event it is."""

    subtype_key: str = ""
    """A second key that refines the kind — `item.type` for a CLI whose every item arrives as
    `item.completed`. An `*_on` entry written `type/subtype` matches only when both agree; a plain
    entry matches on the type alone. Empty means the CLI has no such refinement, and a `type/sub`
    entry can then match nothing rather than something by accident."""

    say_on: tuple[str, ...] = ()
    say_at: str = ""
    """The event types carrying assistant text, and where the text is inside them."""

    done_on: tuple[str, ...] = ()
    done_at: str = ""
    """What ends a turn, and where its final text is."""

    think_on: tuple[str, ...] = ()
    think_at: str = ""
    """The event types carrying the model's thinking, and where it is inside them (D45). Empty is
    the conservative default — a provider file that did not say where thinking is, has none."""

    delta_on: tuple[str, ...] = ()
    delta_kind_at: str = ""
    deltas: tuple[Delta, ...] = ()

    behaviour_args: tuple[BehaviourArg, ...] = ()
    """How a `Behaviour`'s fields become this CLI's flags (D64). A field with no entry has no flag,
    and setting it is reported by `unmapped_behaviour` rather than dropped."""
    """Streamed pieces (D63): the event types that carry them, the field naming which piece, and
    one `Delta` per piece — Claude Code's `stream_event` with `event.delta.type` of
    `thinking_delta` or `text_delta` (measured 2026-09-12 with `--include-partial-messages`).
    Empty is the conservative default: a provider file that did not say streams nothing."""

    interrupt_line: str = ""
    """The line that tells a resident CLI to stop the running turn (D63) — a JSON control message
    on Claude Code's stream-json input. Empty means it cannot be told, and a thread ends a turn by
    closing the session instead. Measured before it is set, never transcribed."""

    failed_at: str = ""
    """A boolean saying the turn failed. Read rather than inferred from an exit code: these CLIs
    exit non-zero for reasons that are not failures and zero for failures that are."""

    failed_text_at: str = ""
    """Where a failed turn says why, when the ending event carries it — `error.message` on Codex's
    `turn.failed` (measured: *You've hit your usage limit…*). Shown as the turn's text when the
    turn failed and said nothing else, so the person reads the reason and not a blank."""

    mcp_config_arg: str = ""
    """The flag that takes an MCP server configuration as JSON. This is how D42's socket closes
    around a CLI of this shape: the run's registry goes in here and its tools become the only ones
    worth having."""

    mcp_config_shape: str = "json"
    """How the configuration is spelled after the flag: `json` is one argument holding
    `{"mcpServers": …}` (Claude Code); `overrides` is one `<flag> mcp_servers.<name>.<field>=<toml>`
    per field (Codex). Measured, both; a third CLI with a third spelling costs a value here."""

    mcp_strict_args: tuple[str, ...] = ()
    """Flags that stop it loading MCP servers from anywhere else. Without them a user's own global
    configuration joins the run ungoverned."""

    allow_arg: str = ""
    """The flag that pre-permits the tools we injected.

    Not a loosening — the opposite. A CLI with its own permission prompt will block an injected tool
    and answer *you have not granted it yet*, which in a non-interactive run is a refusal nobody
    asked for and nobody can answer. Naming our own server here removes **its** gate so that the
    run's governance is the only one left, which is the arrangement D42 wants: one authority, and
    it is ours.
    """

    allow_override: str = ""
    """For a CLI whose configuration is overrides (`mcp_config_shape = "overrides"`): the per-server
    override that pre-permits an injected server's tools, with `{name}` for the server's name.
    Measured on Codex: `mcp_servers.{name}.default_tools_approval_mode="approve"` — without it an
    `exec` run (approval policy `never`) refuses every injected tool that is not read-only with
    *MCP tool call requires approval*. The same argument as `allow_arg`: removing **its** gate
    leaves the run's governance as the only one."""

    allow_tool_prefix: str = ""
    """What the CLI prefixes an injected server's tools with, when naming them to `allow_arg`.

    Measured: Claude Code lists them as `mcp__<server>__<tool>` and accepts `mcp__<server>` to mean
    all of that server's. The prefix is that CLI's convention, so it is on the record rather than in
    the transport — a second CLI with a different one costs a field, not a branch.
    """

    disallow_arg: str = ""
    disallow: tuple[str, ...] = ()
    """The flag that refuses the CLI's own tools, and their names. A provider left holding its
    native file and shell tools does its work outside the registry, where nothing here sees it —
    which is the socket open, not closed."""

    stop_reason_at: str = ""
    cost_usd_at: str = ""
    input_tokens_at: str = ""
    output_tokens_at: str = ""


@dataclass(frozen=True)
class Provider:
    """One provider, as read from its file.

    Every field that encodes a quirk is here rather than in a code path, and the file that carries
    it also carries the measurement that found it.
    """

    id: str
    kind: ProviderKind
    bin: str
    """The executable to look for. Resolution searches more than `PATH` and tries every candidate,
    because an earlier directory can hold a wrapper left by a half-finished install and only
    spawning tells the two apart."""

    name: str = ""
    """What to call it when talking to a person. Falls back to `id` where it is empty."""

    fallback_bins: tuple[str, ...] = ()
    """Drop-in forks that ship an argv-compatible binary under another name, tried in order after
    `bin` itself. A single-binary install of a fork is still this provider."""

    bin_env_key: str | None = None
    """An environment variable that overrides resolution entirely — the escape hatch for a machine
    whose layout nothing here can be expected to guess."""

    version_probe: tuple[str, ...] = ()
    minimum_version: str | None = None
    """Below this, the answer is `too-old` rather than `ready`. Absent means no floor is known, and
    no floor is not the same as *any version will do* — it means nobody has measured one."""

    auth_probe: tuple[str, ...] = ()
    """A cheap, side-effect-free question a provider answers about itself (D41). Empty means it is
    never asked, and its status is `unknown` until a real turn fails."""

    auth_failure_patterns: tuple[str, ...] = ()
    """What its answer looks like when it is *not* signed in. Unmatched output is `unknown`, never
    `ready` — a provider that changed its wording must not read as authenticated."""

    launch_args: tuple[str, ...] = ()
    transport: str | None = None
    """How to talk to it once it is running. An open string; see the module docstring."""

    injects_tools: str | None = None
    """How the run's own registry reaches it — the mechanism D42's socket is closed with. `None` is
    *it has not said*, and a provider whose effects cannot be routed through the registry is refused
    rather than admitted ungoverned."""

    set_env: tuple[EnvVar, ...] = ()
    strip_env: tuple[str, ...] = ()
    """What must **not** be inherited. Measured, never guessed: a CLI that refuses to run inside
    another copy of itself detects that through an inherited variable, and a child launched from
    within one will not start until it is cleared."""

    backfill_env: tuple[str, ...] = ()
    """Variables to supply from the OS when the parent's environment lacks them. A child spawned
    with a stripped environment otherwise fails for want of something nobody forwarded."""

    dialect: Dialect | None = None
    """How to read this provider's stream, when its transport is one that needs telling."""

    install_hint: str = ""
    """What a person would run to get this provider, said when it is absent. Said — never run
    (D41): installing software on somebody's machine is not this library's business."""

    @property
    def called(self) -> str:
        return self.name or self.id


__all__ = ["Delta", "Dialect", "EnvVar", "Provider", "ProviderKind", "ProviderStatus"]
