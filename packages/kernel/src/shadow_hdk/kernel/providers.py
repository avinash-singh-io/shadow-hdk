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

    install_hint: str = ""
    """What a person would run to get this provider, said when it is absent. Said — never run
    (D41): installing software on somebody's machine is not this library's business."""

    @property
    def called(self) -> str:
        return self.name or self.id


__all__ = ["EnvVar", "Provider", "ProviderKind", "ProviderStatus"]
