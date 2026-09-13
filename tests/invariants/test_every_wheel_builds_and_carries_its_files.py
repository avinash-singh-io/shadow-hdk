"""The distribution builds as a wheel and an sdist; the wheel carries the data files its parts
read at runtime (BUG-035, found by the clean-venv install proof), and the sdist carries the source
and nothing of the working tree.

The wheel invariant beside this one reads metadata; nothing built a wheel, so a `force-include`
that duplicated what `packages` already included made the providers unbuildable for five
releases without a test noticing — the sdist built, the wheel raised, and the workspace install
never needed either. This builds both and looks inside. The sdist check came from the first build
of the one distribution (D78): 11 MB, of which 2,273 files were the TypeScript client's
`node_modules` — a nested `.gitignore` the sdist builder did not honour — so what the sdist holds
is declared, not inherited.
"""

from __future__ import annotations

import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

DATA_FILES: tuple[str, ...] = (
    "shadow_hdk/providers/library/claude-code.toml",
    "shadow_hdk/serve/batteries_library/wigolo.toml",
    "shadow_hdk/adapters/agent/library/single.toml",
    "shadow_hdk/adapters/agent/skills_library/verify-before-done.toml",
    "shadow_hdk/py.typed",
)
"""The files the parts read by `importlib.resources` — the ones a source checkout would never
miss and an install would — and the typing marker."""


SDIST_CARRIES: tuple[str, ...] = ("src/shadow_hdk/kernel/__init__.py", "README.md", "LICENSE")
SDIST_NEVER: tuple[str, ...] = ("node_modules", "clients/", "specs/", ".claude/", ".momentum/")
SDIST_CEILING_BYTES = 1_000_000


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    out = tmp_path_factory.mktemp("built")
    done = subprocess.run(
        ["uv", "build", "--out-dir", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    return sorted(out.iterdir())


@pytest.fixture(scope="module")
def wheels(built: list[Path]) -> list[Path]:
    return [p for p in built if p.suffix == ".whl"]


@pytest.fixture(scope="module")
def sdist(built: list[Path]) -> Path:
    found = [p for p in built if p.name.endswith(".tar.gz")]
    assert len(found) == 1, [p.name for p in built]
    return found[0]


def test_the_distribution_builds_one_wheel_and_one_sdist(built: list[Path]) -> None:
    names = [p.name for p in built if p.name != ".gitignore"]
    assert len(names) == 2 and all(n.startswith("shadow_hdk-") for n in names), names


def test_the_sdist_carries_the_source_and_nothing_of_the_working_tree(sdist: Path) -> None:
    with tarfile.open(sdist) as archive:
        names = ["/".join(m.name.split("/")[1:]) for m in archive.getmembers()]
    missing = [f for f in SDIST_CARRIES if f not in set(names)]
    assert not missing, f"the sdist lacks {missing}"
    stray = sorted({n for n in names if any(part in n for part in SDIST_NEVER)})
    assert not stray, f"the working tree rides in the sdist: {stray[:8]} ({len(stray)} files)"
    assert sdist.stat().st_size < SDIST_CEILING_BYTES, f"{sdist.stat().st_size:,} bytes"


def test_the_wheel_carries_the_files_its_parts_read(wheels: list[Path]) -> None:
    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
    missing = [f for f in DATA_FILES if f not in set(names)]
    assert not missing, f"the wheel lacks {missing}"
    assert len(names) == len(set(names)), "a file added twice is a build that will not"
    assert not [n for n in names if "__pycache__" in n], "no caches ride in the wheel"


def test_a_wheel_missing_a_file_would_be_seen(tmp_path: Path) -> None:
    empty = tmp_path / "shadow_hdk_providers-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(empty, "w") as archive:
        archive.writestr("shadow_hdk/providers/__init__.py", "")
    with zipfile.ZipFile(empty) as archive:
        names = set(archive.namelist())
    assert "shadow_hdk/providers/library/claude-code.toml" not in names
