"""Asking a provider about itself, and believing only what it said (D41).

A probe is a cheap, side-effect-free question — a version flag, a status command — and the whole
discipline here is in what happens to an answer nobody can classify.

**Three things a version probe can mean.** It answered (a version). It answered badly but it *is*
the right binary — a CLI that dislikes the flag. Or the *launcher never reached the program at all*:
a wrapper left by a half-finished install starts, runs its interpreter, and only then fails to load
the script it names. The last one is a plain non-zero exit and looks exactly like the middle one,
and the remedies are opposite — abandon this candidate and try the next, versus keep it and stop
looking. So it is decided on the launcher's own vocabulary and nothing broader: over-match here and
a working CLI's user is sent to some other install of it.

**Three things an auth probe can mean**, and the third is the point: signed in, signed out, or
*could not tell*. Unmatched output is `unknown`. It must not read as `ready`, because a CLI that
changed its wording would then look authenticated to a runtime about to spend somebody's money; and
it must not read as `not-signed-in`, because that sends somebody to fix what is not broken.

**No credential survives a probe.** The result is about to be logged, rendered or written to a
diagnostic file. Some status commands print a token; this redacts anything that looks like one
before it can be carried anywhere.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from shadow_hdk.kernel import Provider, ProviderStatus

TIMEOUT_S = 10.0

LAUNCHER_MISSED_ITS_TARGET = (
    re.compile(r"\bMODULE_NOT_FOUND\b"),
    re.compile(r"\bCannot find module\b", re.IGNORECASE),
    re.compile(r"is not recognized as an internal or external command", re.IGNORECASE),
    re.compile(r"The system cannot find the path specified", re.IGNORECASE),
    re.compile(r"CommandNotFoundException", re.IGNORECASE),
)
"""Evidence the launcher never reached the program it stands for.

Deliberately narrow, and deliberately *not* the broader vocabulary of "not installed" or "not on
PATH": a non-zero exit on its own stays a real answer from the right binary.
"""

SECRET = re.compile(
    r"\b(?:sk|pat|ghp|gho|xox[baprs])[-_][A-Za-z0-9_\-]{8,}|\b[A-Fa-f0-9]{32,}\b|"
    r"(?<=token=)\S+|(?<=key=)\S+|(?<=Bearer )\S+"
)
"""What a leaked credential looks like in a status line. Redaction is deliberately eager: a false
positive costs a less readable diagnostic, a false negative writes somebody's key to a log."""

VERSION = re.compile(r"\b(\d+(?:\.\d+)+)\b")


def redacted(text: str) -> str:
    return SECRET.sub("[redacted]", text)


@dataclass(frozen=True)
class Asked:
    """What a probe found. Nothing in here may carry a credential."""

    status: ProviderStatus
    version: str | None = None
    message: str | None = None
    unusable: bool = False
    """This candidate is not the program it claims to be — try the next one."""


def newer_or_same(found: str | None, floor: str) -> bool:
    """Numerically, part by part.

    Lexicographic comparison reports `2.1.235` as older than `2.1.9`, which would refuse a current
    CLI. And a version nothing here can parse — `nightly-abc123` — is **let through**: it is not
    old, it is unparseable, and refusing a working install on a failed string parse is the worse
    error of the two.
    """
    if not found:
        return True
    seen, wanted = VERSION.search(found), VERSION.search(floor)
    if not seen or not wanted:
        return True
    mine = [int(part) for part in seen.group(1).split(".")]
    theirs = [int(part) for part in wanted.group(1).split(".")]
    width = max(len(mine), len(theirs))
    mine += [0] * (width - len(mine))
    theirs += [0] * (width - len(theirs))
    return mine >= theirs


async def _run(argv: list[str], env: Mapping[str, str]) -> tuple[int | None, str]:
    """Run a probe and give back its exit code and everything it said, redacted."""
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=dict(env),
        )
    except OSError as never_started:
        return None, redacted(f"{type(never_started).__name__}: {never_started}")
    try:
        out, err = await asyncio.wait_for(process.communicate(), TIMEOUT_S)
    except TimeoutError:
        process.kill()
        await process.wait()
        return None, "the probe did not answer in time"
    said = f"{out.decode(errors='replace')}\n{err.decode(errors='replace')}"
    return process.returncode, redacted(said)


async def ask_version(provider: Provider, binary: Path, *, env: Mapping[str, str]) -> Asked:
    """What version this candidate is, or why it is not a candidate at all."""
    if not provider.version_probe:
        return Asked(status="ready")

    code, said = await _run([str(binary), *provider.version_probe], env)
    if code is None or any(pattern.search(said) for pattern in LAUNCHER_MISSED_ITS_TARGET):
        return Asked(status="absent", message=said.strip()[:400] or None, unusable=True)

    found = VERSION.search(said)
    version = found.group(1) if found else None
    if provider.minimum_version and not newer_or_same(version, provider.minimum_version):
        return Asked(
            status="too-old",
            version=version,
            message=(
                f"{provider.called} is {version}; {provider.minimum_version} or newer is needed"
            ),
        )
    return Asked(status="ready", version=version)


async def ask_auth(provider: Provider, binary: Path, *, env: Mapping[str, str]) -> Asked:
    """Whether this provider is signed in — asked, never read (D41).

    Nothing opens a credential store, a keychain or a config file. The provider is asked its own
    question and the answer is matched against patterns **on its record**, so teaching this runtime
    a new provider's wording is editing a file.
    """
    if not provider.auth_probe:
        return Asked(status="unknown", message=f"{provider.called} has no way to be asked")

    code, said = await _run([str(binary), *provider.auth_probe], env)
    if code is None:
        return Asked(status="unknown", message=said.strip()[:400] or None)

    for pattern in provider.auth_failure_patterns:
        if re.search(pattern, said, re.IGNORECASE):
            return Asked(status="not-signed-in", message=said.strip()[:400] or None)

    if code == 0:
        return Asked(status="ready")
    # It failed, and nothing on the record explains why. Saying `not-signed-in` here would be a
    # guess dressed as a diagnosis.
    return Asked(status="unknown", message=said.strip()[:400] or None)


__all__ = ["Asked", "ask_auth", "ask_version", "newer_or_same", "redacted"]
