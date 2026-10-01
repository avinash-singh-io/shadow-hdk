"""The field's own two file formats, read as the kit's own shapes (ENH-047, lane P's asks 5 and 11).

Two readers, both **optional and both composed by a product** — neither is a default and neither is
an agent tool.

* `root_instructions` reads a root's `AGENTS.md` or `CLAUDE.md` as named `Fragment`s (D169).
* `MarkdownSkills` reads a directory of `SKILL.md` files as a `SkillSource`.

**On the instruction files, the existing default stays.** A governed Claude Code does not read a
folder's instruction files — `--setting-sources ""` plus auto-memory off (ENH-012), measured — and
that is deliberate: a run's instructions should be the mode's behaviour, not a file somebody left in
a folder for a different tool. What was missing is the other half. *The kit never offered them
either*, so a team convention written where the field writes it reached no provider, and a
key-backed model never had them at all.

So this reads them **as data a mode frames** — named, attributable, and refusable because a product
chooses whether to pass them at all. That is the difference between offering a convention and
obeying an unmarked file.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from shadow_hdk.adapters.agent.skills import Skill
from shadow_hdk.kernel.providers import Fragment

INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md")
"""What the field writes, in the order a reader should prefer. Not exhaustive and not a standard —
a caller naming its own is the ordinary case."""


def root_instructions(
    root: Path | str,
    *,
    names: Sequence[str] = INSTRUCTION_FILES,
    limit: int = 32_000,
) -> tuple[Fragment, ...]:
    """A root's own instruction files, as fragments a mode can frame (D169).

    Returns `()` where there are none, which is the common case and not an error. A file too large
    to carry is **truncated and said so** rather than dropped: half a convention is better than
    silence, and silence is what a product would have to debug.

    Nothing here decides that a run gets these — a product passes them to `Behaviour.fragments` or
    it does not. That is the whole point of returning data rather than installing a default.
    """
    where = Path(root)
    found: list[Fragment] = []
    for name in names:
        path = where / name
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            # Unreadable, absent, or not text. A convention nobody can read is not a convention,
            # and failing the run over it would be worse than going without.
            continue
        if not text.strip():
            continue
        if len(text) > limit:
            text = text[:limit] + f"\n\n[… truncated at {limit} characters]"
        found.append(Fragment(name=name, text=text.strip(), source=f"the root {where.name}"))
    return tuple(found)


# ------------------------------------------------------------------ SKILL.md


def _front_matter(text: str) -> tuple[dict[str, str], str]:
    """A leading `---` block as keys, and whatever follows as the body.

    Deliberately not a YAML parser. The field's `SKILL.md` front matter in practice is flat
    `key: value` lines, and pulling a YAML dependency in to read three of them would be the
    "a parser is a phase" trade this project refuses elsewhere (D158). A file whose front matter
    needs more than this is one a product should read itself.
    """
    if not text.startswith("---"):
        return {}, text
    rest = text[3:].lstrip("\n")
    end = rest.find("\n---")
    if end == -1:
        return {}, text
    head, body = rest[:end], rest[end + 4 :]
    keys: dict[str, str] = {}
    for line in head.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if sep:
            keys[key.strip().lower()] = value.strip().strip("'\"")
    return keys, body.lstrip("\n")


def skill_from_markdown(text: str, *, where: str, source: str = "file") -> Skill:
    """One `SKILL.md` as a `Skill`: front matter for the name and description, the body as the
    prompt. `name` falls back to the containing directory, which is how the field names them."""
    keys, body = _front_matter(text)
    name = keys.get("name", "").strip()
    if not name:
        raise ValueError(f"{where}: needs a name, in front matter or from its directory")
    if not body.strip():
        raise ValueError(f"{where}: has no body, so there is no procedure in it")
    needs = [n.strip() for n in keys.get("needs", "").replace(",", " ").split() if n.strip()]
    return Skill(
        name=name,
        prompt=body.strip(),
        needs=frozenset(needs),
        description=" ".join(keys.get("description", "").split()),
        source=source,
    )


class MarkdownSkills:
    """Every `SKILL.md` under a directory, as a `SkillSource` (lane P's ask 11).

    The field's layout is `<dir>/<skill-name>/SKILL.md`, so a file with no `name` in its front
    matter takes its directory's name — which is what makes an existing folder of skills work
    unchanged. A file that cannot be read is **skipped, not fatal**: one malformed skill must not
    take the other twenty down with it.
    """

    def __init__(self, where: Path | str, *, source: str = "markdown") -> None:
        self.where = Path(where)
        self.source = source
        self.skipped: list[str] = []
        """What could not be read, and why — so a product can show it rather than wonder."""

    async def skills(self) -> Sequence[Skill]:
        found: list[Skill] = []
        self.skipped = []
        if not self.where.is_dir():
            return ()
        for path in sorted(self.where.rglob("SKILL.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, ValueError) as unreadable:
                self.skipped.append(f"{path}: {unreadable}")
                continue
            keys, _ = _front_matter(text)
            if not keys.get("name"):
                text = f"---\nname: {path.parent.name}\n" + text.removeprefix("---\n")
            try:
                found.append(skill_from_markdown(text, where=str(path), source=self.source))
            except ValueError as wrong:
                self.skipped.append(str(wrong))
        return tuple(found)


def markdown_skills(where: Path | str, *, source: str = "markdown") -> MarkdownSkills:
    return MarkdownSkills(where, source=source)


__all__ = [
    "INSTRUCTION_FILES",
    "MarkdownSkills",
    "markdown_skills",
    "root_instructions",
    "skill_from_markdown",
]
