"""A provider is a file (D40), by a test: no vendor's name in the code of the kernel or the
runtime.

The rule that inference is one pluggable seam — any key, any endpoint, a local model, a desktop
subscription CLI — and that nothing else in the kit knows which provider is in use, held by
discipline until 0.34. This walks the *code* of `kernel/` and `runtime/` (docstrings and comments
stripped, so a measured fact may still be explained where it matters) and refuses a vendor's name
in an identifier, a string or a keyword: the day someone writes `if provider == "codex"` in the
runtime, this fails. The adapters and the provider files are where those names belong.
"""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "shadow_hdk"
VENDORS = ("claude", "codex", "anthropic", "openai", "ollama", "opencode", "langchain")
WALKED = ("kernel", "runtime")


def code_tokens(source: str) -> list[str]:
    """Every NAME and STRING token — comments and docstrings left out, so prose may explain a
    measured fact (`kernel/providers.py` does, at length) without the code depending on it."""
    kept: list[str] = []
    previous = tokenize.INDENT
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.STRING and previous in (
            tokenize.INDENT,
            tokenize.NEWLINE,
            tokenize.NL,
            tokenize.DEDENT,
            tokenize.ENCODING,
        ):
            previous = tok.type
            continue  # a docstring: a string that is a statement of its own
        if tok.type in (tokenize.NAME, tokenize.STRING):
            kept.append(tok.string)
        if tok.type not in (tokenize.COMMENT, tokenize.NL):
            previous = tok.type
    return kept


def vendor_mentions(root: Path) -> list[str]:
    found: list[str] = []
    for part in WALKED:
        for source in sorted((root / part).rglob("*.py")):
            for token in code_tokens(source.read_text(encoding="utf-8")):
                lowered = token.lower()
                for vendor in VENDORS:
                    if vendor in lowered:
                        found.append(f"{source.relative_to(root)}: {token!r} ({vendor})")
    return found


def test_the_kernel_and_the_runtime_name_no_vendor() -> None:
    offenders = vendor_mentions(SRC)
    assert not offenders, "\n  ".join(["a vendor's name in code below the adapters:", *offenders])


def test_the_walk_catches_what_it_looks_for(tmp_path: Path) -> None:
    """The invariant's own proof: a planted name is found; the same name in a docstring or a
    comment is not — prose is allowed to say what was measured."""
    planted = tmp_path / "kernel"
    planted.mkdir()
    (tmp_path / "runtime").mkdir()
    (planted / "x.py").write_text(
        '"""Claude Code answers on stdout — a docstring may say so."""\n'
        "# and a comment may say codex\n"
        'def pick(provider: str) -> bool:\n    return provider == "codex"\n',
        encoding="utf-8",
    )
    found = vendor_mentions(tmp_path)
    assert found == ["kernel/x.py: '\"codex\"' (codex)"], found
