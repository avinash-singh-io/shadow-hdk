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

from dataclasses import dataclass, field, replace
from typing import Literal

from shadow_hdk.kernel.capabilities import ProviderCapabilities

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
class Carried:
    """What a resolved agent contributes to the behaviour a provider is opened with (H11-B).

    Plain data rather than a `Pattern`, because a provider that owns its own loop cannot be handed a
    loop — and because the runtime composing this must not learn what a `Pattern` is (the layering
    rule an invariant enforces). `tool_names=None` means *all of the run's*, exactly as an unset
    `tools_offered` does.
    """

    instructions: str = ""
    tool_names: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Fragment:
    """One named, attributable piece of what a run carries into a model (D166, Epic 0011 phase 62).

    A mode's instructions, a root's `AGENTS.md`, a product's house style, a team convention — all
    one shape, because four mechanisms for four kinds of context would give four ways to be wrong,
    and a model that has learnt to read one block has learnt to read all of them.

    **Named and attributable on purpose.** Lane P asked for context that is "named, attributable,
    refusable, not an unmarked prefix", and the reason is what an unmarked prefix does to a model:
    it reads as the person talking, so it gets argued with instead of followed — or worse, a file
    somebody left in a folder reads with the same authority as the mode. `name` says what this is;
    `source` says where it came from, so a model (and a person reading the record) can weigh it.
    """

    name: str
    text: str
    source: str = ""


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

    silence_seconds: float | None = None
    """How long this mode lets a CLI say **nothing** before its turn is given up (D182, BUG-233).

    A field the kit honours itself rather than one a CLI is handed, like `tools_offered` — no
    provider has a flag for our patience. `None` is the adapter's default. It is a ceiling on the
    *gap between frames*, not on the turn: a run that keeps streaming is working, however long it
    takes, and before phase 65 a fixed ten minutes of total turn time failed real work.
    """
    fragments: tuple[Fragment, ...] = ()
    """Named context this run carries besides the instructions (D166). Empty changes nothing.

    A product's own fragments go here; so does a root's `AGENTS.md` where a plugin asked for it
    (D169). They are delivered to a CLI and to a key-backed model by the same derivation, which is
    what makes "identically for both" a property rather than an intention (D167)."""


@dataclass(frozen=True)
class BehaviourArg:
    """One behaviour field, and the flag the CLI takes it as (D64)."""

    field: str
    flag: str
    template: str = ""
    """How the value is spelled after the flag, when the CLI takes it as `key=value` rather than
    as a flag of its own: `{value}` is where the value goes — Codex's reasoning effort is
    `-c model_reasoning_effort="{value}"` (ENH-028). Empty: the value as is."""


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

    instructions_in_prompt: bool = False
    """Whether this CLI can be told who to be **in the turn**, when it maps no flag for it
    (Epic 0011 Q1).

    The other half of D64. `behaviour_args` says which fields a CLI takes as flags; every field it
    does not take was named on `unmapped_behaviour` and then dropped, which for `codex exec` meant a
    product's `system` prompt reached Claude Code and not Codex. A CLI with no `--system-prompt` can
    still be handed one as framed text at the top of its first turn, and whether that is true of a
    given CLI is a fact about it — so it is a field here rather than a branch above.

    **Default false, like every other default in this record.** A CLI nobody has measured is not
    handed a prompt shape somebody guessed at; folding into the turn changes what the model reads,
    and inventing that is the cost this record refuses everywhere else. A CLI that *does* map a flag
    for a field is never also folded — it would send the same role twice and be billed twice.
    """

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
    session_gone_matches: tuple[str, ...] = ()
    """Substrings that, in a failed turn's text or on the CLI's stderr, mean the session it was
    asked to resume is gone (D139). Measured 2026-09-20: Claude Code 2.1.278 answers a `result`
    with `is_error: true` and `errors: ["No conversation found with session ID: …"]`; Codex
    0.154.0 writes `no rollout found for thread id …` to stderr and nothing to stdout."""
    cache_read_tokens_at: str = ""
    cache_write_tokens_at: str = ""
    """Where the ending event says what the cache did (D141): `usage.cached_input_tokens` and
    `usage.cache_write_input_tokens` on Codex; `usage.cache_read_input_tokens` and
    `usage.cache_creation_input_tokens` on Claude Code. Empty where a CLI does not say."""


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

    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    """Evidence-backed execution facts. Omitted axes remain unknown, never permission."""

    @property
    def called(self) -> str:
        return self.name or self.id


INSTRUCTION_FIELDS = ("system", "append_system")
"""The behaviour fields a turn's own text can carry. `model` and `effort` are launch decisions and
`temperature` is a sampling parameter — asking for those in prose is asking, not setting."""


def unmapped_behaviour(provider: Provider, behaviour: Behaviour | None) -> list[str]:
    """Behaviour fields this provider has no way to take, that the behaviour set. Named, not dropped
    (D64, ENH-020) — a host learns its mode asked for something this CLI cannot do. Pure over
    the record and the behaviour, so every opener reads the same answer: the JSONL opener from
    the record's `behaviour_args`, ACP from a record that maps none.

    **A flag is not the only way to be told.** A dialect that takes instructions in the turn
    (`instructions_in_prompt`) delivers `system` and `append_system`, so naming them here would be
    a lie — and a lie a host acts on, because lane P hides the controls this field reports. Epic
    0011 Q1. `temperature` is still named for such a CLI: a turn's text cannot set one.

    **`tools_offered` is not one of the fields reported here**, and until phase 65 this function
    pretended otherwise: it unioned the name into `mapped`, which was **dead code** — the loop below
    walks five field names and that is not one of them, so the union could never change an answer.
    Found by a mutation that deleted it and survived. The field is honoured by the kit rather than
    by the CLI: the registry serving the run's tools narrows its listing to the offered set before
    the CLI ever lists (D178, BUG-230). A narrowing is therefore neither reported nor dropped.
    """
    if behaviour is None:
        return []
    dialect = provider.dialect or Dialect()
    mapped = {a.field for a in dialect.behaviour_args}
    if dialect.instructions_in_prompt:
        mapped |= set(INSTRUCTION_FIELDS)
    unmapped: list[str] = []
    for name in ("system", "append_system", "model", "effort", "temperature"):
        if name in mapped:
            continue
        value = getattr(behaviour, name, None)
        if value not in (None, "", ()):
            unmapped.append(name)
    return unmapped


def carried_into(
    behaviour: Behaviour | None,
    *,
    instructions: str,
    tool_names: tuple[str, ...] | None,
) -> Behaviour | None:
    """A mode's behaviour with a resolved agent's role and tool list composed in (H11-B).

    For a provider that owns its own loop. A CLI gets *everything but the loop* — its instructions
    through the flag-or-fold path (D64, ENH-051) and its tool list through the registry narrowing
    (D178) — and both of those shipped before this; what was missing was the composition. Until
    phase 66 a mode naming an agent on Claude Code or Codex got **nothing at all**, silently
    (H11-A named the silence; this ends it).

    **Instructions layer, agent first.** D168's rule, reused rather than reinvented: a mode's words
    go *onto* the role and never replace it, because the role is who the agent is and the mode is
    what this run wants of it. Reversed, a mode's aside would outrank the role and the agent would
    stop being that agent.

    **Tool lists intersect, and never widen.** Both are allow-lists over one registry. D178 made
    narrowing safe by applying it last so it can only take away; two allow-lists where the later
    widened the earlier would break exactly that, and a mode could be handed more than its policy
    left by naming an agent. The mode's order is kept, because a catalogue with two sources of
    ordering has none.

    `tool_names=None` means *all of the run's*, as an unset `tools_offered` does — so it leaves the
    mode's list alone. An explicitly empty tuple has said something, and it is not *everything*.

    A behaviour with nothing to compose comes back **unchanged, not copied**: a rebuilt `system`
    reaches a CLI's flag and is paid for, so identity matters here.
    """
    if not instructions and tool_names is None:
        return behaviour
    base = behaviour if behaviour is not None else Behaviour()
    system = base.system
    if instructions:
        system = f"{instructions}\n\n{system}" if system else instructions
    offered = base.tools_offered
    if tool_names is not None:
        wanted = set(tool_names)
        offered = tuple(n for n in offered if n in wanted) if offered else tuple(tool_names)
    return replace(base, system=system, tools_offered=offered)


def narrowed(names: tuple[str, ...], behaviour: Behaviour | None) -> tuple[str, ...]:
    """The names a step is shown, narrowed to the subset its mode asked for (D178).

    **Applied last, so it can only ever take away.** A mode naming a tool the policy already
    refused does not get it back — the narrowing is an intersection with what was going to be shown
    anyway, never a union. That is what makes `tools_offered` safe to put on a mode: no mode can
    widen past its own policy by listing a name.

    The run's order is kept, not the mode's. A catalogue that reshuffled because a mode happened to
    list its names in another order would make the offered set a second source of ordering, and a
    model reads a catalogue top to bottom.

    An empty `tools_offered` is *all of the run's* (the field's documented default), so a mode that
    names nothing is shown everything — which is every mode written before this phase.

    Until phase 65 the field parsed and narrowed nothing, while two honesty fields reported it
    honoured (BUG-230). One derivation, because there are genuinely two catalogues — the one an
    in-process loop builds for a key-backed model and the one the registry serves a CLI over MCP —
    and two that drifted is how the claim came to be false in the first place.
    """
    if behaviour is None or not behaviour.tools_offered:
        return names
    wanted = set(behaviour.tools_offered)
    return tuple(name for name in names if name in wanted)


def unanswered(names: tuple[str, ...], behaviour: Behaviour | None) -> tuple[str, ...]:
    """Names in `tools_offered` that nothing in the run answers to, sorted (D179).

    The D176 cut, again: a typo in a narrowing would otherwise be invisible, because a name that
    matches nothing simply narrows nothing and the step runs looking right. Sorted so a refusal
    reads the same twice.

    Empty in, empty out — an unset `tools_offered` means *all of them*, not *none of them named
    wrongly*, so it has nothing unanswered. That falls out of the difference rather than needing a
    guard of its own: an early return for it was an equivalent mutant, which is to say a branch no
    test could ever distinguish.
    """
    if behaviour is None:
        return ()
    return tuple(sorted(set(behaviour.tools_offered) - set(names)))


def carried_by(behaviour: Behaviour | None, *, instructions: bool = True) -> tuple[Fragment, ...]:
    """Everything a behaviour carries, as fragments, in the order a model should read it (D166).

    `instructions=False` leaves out `system`/`append_system` — for a CLI whose own flag already
    delivers them, where carrying them again would send the role twice and be billed twice.
    """
    if behaviour is None:
        return ()
    found: list[Fragment] = []
    if instructions:
        for name in INSTRUCTION_FIELDS:
            text = str(getattr(behaviour, name, "") or "")
            if text:
                found.append(Fragment(name="instructions", text=text, source="the mode"))
    found.extend(behaviour.fragments)
    return tuple(found)


def framed(fragments: tuple[Fragment, ...]) -> str:
    """Fragments as one block of text a model can tell apart from a person's words (D167).

    **The one assembler**, used for a CLI's turn and a key-backed model's system message alike.
    Before this there were two paths and they had already diverged: Q1 folded instructions into a
    CLI's prompt while a key-backed model got nothing at all (BUG-229). One derivation is what
    makes "identically for both" checkable.

    Empty in, empty out — a run carrying nothing adds no framing, so a prompt with no fragments is
    byte-for-byte the prompt it always was.
    """
    if not fragments:
        return ""
    blocks: list[str] = []
    for one in fragments:
        opened = f'<context name="{one.name}"'
        if one.source:
            opened += f' source="{one.source}"'
        blocks.append(f"{opened}>\n{one.text}\n</context>")
    return "\n\n".join(blocks)


def unmapped_for_a_model(
    behaviour: Behaviour | None, *, selects_model: bool = True
) -> tuple[str, ...]:
    """What a key-backed model cannot honour, named (BUG-229, D170).

    `ModelRequest` carries `messages`, `tools` and `model`. So instructions and fragments are
    delivered (through the system message), and `effort` and `temperature` have **nowhere to go** —
    inventing a field for them would be a kernel change, and claiming they were honoured is the lie
    this exists to stop.

    **`model` depends on the port** (`selects_model`, D180, BUG-231). The field is on the request,
    so a port is expected to read it, and the default is that one does — a port that says nothing is
    taken at its word, because the kit's own adapter is the one that has to be accurate. But a
    `LangChainModel` built by `over()` wraps a chat model somebody else configured and genuinely
    cannot be re-specified, so it reports `selects_model` false and `model` is named here. Phase 62
    said *`model` is delivered — the field was already there* while the only real adapter discarded
    it; the field being present is not the same as it being read.

    `tools_offered` is not named: the catalogue this loop hands the model is narrowed to the
    offered set (D178), so it is honoured before the request is built. That sentence stood here
    from phase 62 while **nothing narrowed anything** (BUG-230); phase 65 made it true rather than
    softening it, because the field is what a product plans against.
    """
    if behaviour is None:
        return ()
    cannot = ["effort", "temperature"] if selects_model else ["model", "effort", "temperature"]
    return tuple(name for name in cannot if getattr(behaviour, name, None) not in (None, "", ()))


def instructions_for_prompt(provider: Provider, behaviour: Behaviour | None) -> str:
    """What this CLI must be handed in its turn, framed — or `""` where it needs nothing.

    **Two gates, not one, and conflating them was a real bug.** They are different questions:

    * *Instructions* (`system`, `append_system`) travel in the turn only where the CLI takes them
      that way (`instructions_in_prompt`) **and** no `behaviour_args` flag already delivers them.
      Per field, because a CLI taking `--system-prompt` and no append flag still needs the second.
      A field a flag carries is left out: a role sent twice is paid for twice.
    * *Fragments* travel **always**. No CLI has a flag for a product's named context, so the turn is
      the only way in — for every provider, whether or not it has a system-prompt flag of its own.

    Written first as one gate, which meant Claude Code — which has the flag, so
    `instructions_in_prompt` is false — received **no fragments at all**. Every unit test passed,
    because they all used a dialect that folds. A live measurement found it: the model answered by
    summarising its own system prompt, with our fragment nowhere in it.
    """
    if behaviour is None:
        return ""
    dialect = provider.dialect or Dialect()
    by_flag = {a.field for a in dialect.behaviour_args}
    carried: list[Fragment] = []
    if dialect.instructions_in_prompt:
        carried.extend(
            Fragment(name="instructions", text=text, source="the mode")
            for name in INSTRUCTION_FIELDS
            if name not in by_flag and (text := str(getattr(behaviour, name, "") or ""))
        )
    carried.extend(behaviour.fragments)
    return framed(tuple(carried))


__all__ = [
    "Delta",
    "Dialect",
    "EnvVar",
    "Fragment",
    "INSTRUCTION_FIELDS",
    "Carried",
    "carried_by",
    "carried_into",
    "unmapped_for_a_model",
    "framed",
    "Provider",
    "ProviderKind",
    "ProviderStatus",
    "instructions_for_prompt",
    "unmapped_behaviour",
]
