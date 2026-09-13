"""Every distribution builds as a wheel, and each wheel carries the data files its package
reads at runtime (BUG-035, found by the clean-venv install proof).

The wheel invariant beside this one reads metadata; nothing built a wheel, so a `force-include`
that duplicated what `packages` already included made `shadow-hdk-providers` unbuildable for
five releases without a test noticing — the sdist built, the wheel raised, and the workspace
install never needed either. This builds all eighteen once and looks inside.
"""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / "packages"

DATA_FILES: dict[str, tuple[str, ...]] = {
    "shadow_hdk_providers": ("shadow_hdk/providers/library/claude-code.toml",),
    "shadow_hdk_serve": ("shadow_hdk/serve/batteries_library/wigolo.toml",),
    "shadow_hdk_adapters_agent": (
        "shadow_hdk/adapters/agent/library/single.toml",
        "shadow_hdk/adapters/agent/skills_library/verify-before-done.toml",
    ),
}
"""Wheel → the files a package reads by `importlib.resources`; the ones a source checkout would
never miss and an install would."""


@pytest.fixture(scope="module")
def wheels(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    out = tmp_path_factory.mktemp("wheels")
    done = subprocess.run(
        ["uv", "build", "--all-packages", "--wheel", "--out-dir", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    return sorted(out.glob("*.whl"))


def test_every_distribution_builds_a_wheel(wheels: list[Path]) -> None:
    on_disk = 5 + len([p for p in (PACKAGES / "adapters").iterdir() if p.is_dir()])
    assert len(wheels) == on_disk, [w.name for w in wheels]
    assert all(w.name.startswith("shadow_hdk") for w in wheels)


def test_each_wheel_carries_the_files_its_package_reads(wheels: list[Path]) -> None:
    by_name = {w.name.split("-")[0]: w for w in wheels}
    for distribution, files in DATA_FILES.items():
        assert distribution in by_name, f"no wheel for {distribution}"
        with zipfile.ZipFile(by_name[distribution]) as archive:
            names = set(archive.namelist())
        missing = [f for f in files if f not in names]
        assert not missing, f"{distribution} wheel lacks {missing}"
        assert len(names) == len(set(names)), "a file added twice is a build that will not"


def test_a_wheel_missing_a_file_would_be_seen(tmp_path: Path) -> None:
    empty = tmp_path / "shadow_hdk_providers-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(empty, "w") as archive:
        archive.writestr("shadow_hdk/providers/__init__.py", "")
    with zipfile.ZipFile(empty) as archive:
        names = set(archive.namelist())
    assert "shadow_hdk/providers/library/claude-code.toml" not in names
