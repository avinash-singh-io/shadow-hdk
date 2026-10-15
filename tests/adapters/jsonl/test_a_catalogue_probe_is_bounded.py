"""Every refusal the bounded metadata probe claims, exercised against a real child process.

The happy path, invalid JSON, an empty row list, a row missing a required field and cancellation
are covered by `test_governed_cli_bootstrap`. What is left is the rest of the probe's own
contract: a document of the wrong shape, a response too large to hold, a probe that never
answers, one that fails, and the optional-field rule. Each is a refusal rather than permission to
launch with the SDK's unrestricted defaults, which is the whole point of reading the catalogue.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from shadow_hdk.adapters.jsonl import catalogue as probe
from shadow_hdk.kernel import CatalogueField, LaunchCatalogue

pytestmark = [pytest.mark.anyio, pytest.mark.timeout(120)]


def _spec(*fields: CatalogueField) -> LaunchCatalogue:
    return LaunchCatalogue(
        probe_args=("metadata",),
        entries_at="models",
        replace_fields=fields or (CatalogueField(name="native", value=False),),
        config_arg="--catalogue",
        config_template="{path}",
    )


def _stub(tmp_path: Path, body: str) -> Path:
    cli = tmp_path / "cli"
    cli.write_text(f"#!/usr/bin/env python3\nimport sys,time\n{body}\n")
    cli.chmod(0o755)
    return cli


async def _run(cli: Path, tmp_path: Path, spec: LaunchCatalogue | None = None) -> tuple[str, ...]:
    directory = tmp_path / "home"
    directory.mkdir(exist_ok=True)
    return await probe.prepare_catalogue(
        spec or _spec(), binary=cli, env={**os.environ}, directory=directory
    )


@pytest.mark.parametrize(
    "emitted, complaint",
    [
        ("[]", "must be a JSON object"),
        ('{"other":[{"native":true}]}', "nonempty model rows"),
        ('{"models":"not a list"}', "nonempty model rows"),
        ('{"models":["not an object"]}', "lacks a required field"),
    ],
)
async def test_a_document_of_the_wrong_shape_is_refused(
    tmp_path: Path, emitted: str, complaint: str
) -> None:
    cli = _stub(tmp_path, f"print({emitted!r})")
    with pytest.raises(RuntimeError, match=complaint):
        await _run(cli, tmp_path)


async def test_a_probe_that_fails_is_refused_and_names_its_exit(tmp_path: Path) -> None:
    cli = _stub(tmp_path, 'print(\'{"models":[{"native":true}]}\')\nsys.exit(3)')
    with pytest.raises(RuntimeError, match="exited 3"):
        await _run(cli, tmp_path)


async def test_a_response_too_large_to_hold_is_refused_rather_than_truncated(
    tmp_path: Path,
) -> None:
    """At the shipped bound, not a lowered one: a probe may not evade the cap by overrunning it."""
    cli = _stub(
        tmp_path,
        "sys.stdout.write('x' * 65536)\n"
        f"sys.stdout.write('y' * {probe.CATALOGUE_BYTES})\nsys.stdout.flush()",
    )
    with pytest.raises(RuntimeError, match="exceeded its output limit"):
        await _run(cli, tmp_path)


async def test_an_oversized_error_stream_is_refused_too(tmp_path: Path) -> None:
    """The diagnostic stream is bounded on its own, so a quiet probe cannot flood memory with it."""
    cli = _stub(
        tmp_path,
        'print(\'{"models":[{"native":true}]}\')\n'
        "sys.stderr.write('e' * 200000)\nsys.stderr.flush()",
    )
    with pytest.raises(RuntimeError, match="exceeded its output limit"):
        await _run(cli, tmp_path)


async def test_a_probe_that_never_answers_times_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The deadline is the mechanism under test, so it is shortened rather than waited out."""
    monkeypatch.setattr(probe, "PROBE_SECONDS", 1.0)
    cli = _stub(tmp_path, "time.sleep(120)")
    with pytest.raises(RuntimeError, match="timed out"):
        await _run(cli, tmp_path)


async def test_an_optional_field_is_injected_when_absent_and_every_other_field_is_kept(
    tmp_path: Path,
) -> None:
    """`require_present` governs whether a row must already carry the field, never whether the
    replacement is applied — a switch the host asked to force is forced on rows that omit it."""
    import json

    cli = _stub(
        tmp_path,
        "print(json.dumps({'models':[{'native':True,'context':777,'role':'unchanged'}]}))",
    )
    cli.write_text(cli.read_text().replace("import sys,time", "import sys,time,json"))
    cli.chmod(0o755)
    spec = _spec(
        CatalogueField(name="native", value=False),
        CatalogueField(name="shell", value=False, require_present=False),
    )
    argument, written = await _run(cli, tmp_path, spec)
    assert argument == "--catalogue"
    row = json.loads(Path(written).read_text())["models"][0]
    assert row["native"] is False, "the required replacement must be applied"
    assert row["shell"] is False, "an optional replacement must be injected when absent"
    assert row["context"] == 777 and row["role"] == "unchanged", "other metadata must survive"
