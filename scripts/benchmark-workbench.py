#!/usr/bin/env python3
"""Pinned generated repository: 100k searchable files plus 100k ignored files, no network."""

import argparse
import asyncio
import json
import platform
import subprocess
import tempfile
import time
from pathlib import Path

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.adapters.environment.history import GitHistory


async def benchmark(count: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="hdk-workbench-benchmark-") as temporary:
        root = Path(temporary)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Benchmark"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "benchmark@example.com"], cwd=root, check=True
        )
        (root / ".gitignore").write_text("node_modules/\n")
        for group in range((count + 999) // 1000):
            source = root / "src" / f"{group:03}"
            ignored = root / "node_modules" / f"{group:03}"
            source.mkdir(parents=True)
            ignored.mkdir(parents=True)
            for number in range(group * 1000, min(count, (group + 1) * 1000)):
                (source / f"{number:06}.txt").write_text("ordinary source content\n")
                (ignored / f"{number:06}.txt").write_text("ignored dependency content\n")
        target = root / "src" / "000" / "000000.txt"
        target.write_text("benchmark_needle\n")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "pinned generated fixture v1"], cwd=root, check=True
        )
        history = GitHistory(root)
        env = await LocalEnvironment.open(root, mode="full")
        timings: dict[str, float] = {}

        async def measured(name: str, operation: object) -> object:
            began = time.perf_counter()
            answer = await operation  # type: ignore[misc]
            timings[name] = round(time.perf_counter() - began, 4)
            return answer

        try:
            await measured("glob", env.invoke("glob", {"pattern": "**/000000.txt"}))
            await measured(
                "grep", env.invoke("grep", {"pattern": "benchmark_needle", "glob": "**/000000.txt"})
            )
            before = await measured("snapshot_cold", history.snapshot("cold"))
            await measured("snapshot_unchanged", history.snapshot("unchanged"))
            target.write_text("edited by a shell\n")
            await measured("snapshot_one_edit", history.snapshot("one edit"))
            (root / "new.txt").write_text("created by a shell\n")
            await measured("restore", history.restore(str(before)))
            if target.read_text() != "benchmark_needle\n" or (root / "new.txt").exists():
                raise RuntimeError("restore did not reproduce fixture")
        finally:
            await env.close()
        return {
            "fixture": "workbench-v1",
            "files": count,
            "ignored_files": count,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "git": subprocess.check_output(["git", "--version"], text=True).strip(),
            "seconds": timings,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", type=int, default=100_000)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(benchmark(args.files)), indent=2))
