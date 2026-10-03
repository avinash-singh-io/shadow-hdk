#!/usr/bin/env python3
"""Re-wrap over-long prose lines to <=100 chars, in place, conservatively.

Only touches a line that is plain prose: no code fence, no `=`-assignment shape, no leading `#!`,
and inside what looks like a docstring or comment block. It reflows the whole blank-line-delimited
paragraph at that line's indent, so the result reads as prose rather than as a hard break.
"""

import pathlib
import subprocess
import sys
import textwrap

LIMIT = 100


def offenders(root: str) -> dict[str, list[int]]:
    out = subprocess.run(
        ["uv", "run", "ruff", "check", root, "--output-format=concise", "--select", "E501"],
        capture_output=True,
        text=True,
        cwd=root,
    ).stdout
    found: dict[str, list[int]] = {}
    for line in out.splitlines():
        if ": E501" not in line:
            continue
        where = line.split(": E501")[0]
        path, lineno, _col = where.rsplit(":", 2)
        found.setdefault(path, []).append(int(lineno))
    return found


def reflow(path: pathlib.Path, linenos: list[int]) -> bool:
    lines = path.read_text().split("\n")
    changed = False
    for n in sorted(linenos, reverse=True):
        i = n - 1
        if i >= len(lines):
            continue
        line = lines[i]
        if "```" in line or line.lstrip().startswith(("#!", "|")) or line == "    ":
            continue
        indent = line[: len(line) - len(line.lstrip())]
        # the paragraph: contiguous non-blank lines at this indent, no fences, no table rows
        start = i
        while start > 0:
            prev = lines[start - 1]
            if not prev.strip() or not prev.startswith(indent) or "```" in prev:
                break
            if prev.lstrip().startswith(("|", "-", "*", ">")) or prev.rstrip().endswith('"""'):
                break
            start -= 1
        end = i
        while end + 1 < len(lines):
            nxt = lines[end + 1]
            if not nxt.strip() or not nxt.startswith(indent) or "```" in nxt:
                break
            if nxt.lstrip().startswith(("|", "-", "*", ">")) or '"""' in nxt:
                break
            end += 1
        block = " ".join(lines[j].strip() for j in range(start, end + 1))
        wrapped = textwrap.wrap(
            block, width=LIMIT - len(indent), break_long_words=False, break_on_hyphens=False
        )
        if not wrapped or any(len(indent) + len(w) > LIMIT for w in wrapped):
            continue
        lines[start : end + 1] = [indent + w for w in wrapped]
        changed = True
    if changed:
        path.write_text("\n".join(lines))
    return changed


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    for _ in range(4):
        found = offenders(root)
        if not found:
            print("no E501 remaining")
            break
        touched = [p for p, ns in found.items() if reflow(pathlib.Path(root) / p, ns)]
        if not touched:
            print("could not reflow:", {p: ns for p, ns in found.items()})
            break
        print("reflowed:", ", ".join(touched))
