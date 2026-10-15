"""A bounded SDK metadata probe; literal provider data, never a vendor branch."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path

from shadow_hdk.kernel import LaunchCatalogue
from shadow_hdk.runtime.processes import start_held, stop_or_kill
from shadow_hdk.runtime.resources import settle_resources

PROBE_SECONDS = 30.0
CATALOGUE_BYTES = 8 * 1024 * 1024


async def _bounded(stream: asyncio.StreamReader, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while chunk := await stream.read(65536):
        size += len(chunk)
        if size > limit:
            raise RuntimeError("SDK catalogue probe exceeded its output limit")
        chunks.append(chunk)
    return b"".join(chunks)


async def prepare_catalogue(
    spec: LaunchCatalogue, *, binary: Path, env: Mapping[str, str], directory: Path
) -> tuple[str, ...]:
    """Read local metadata once and retain every field except the specified replacements.

    Unsupported probes, incomplete rows and oversized/hung responses are errors, not
    permission to launch with the SDK's unrestricted defaults. Even cancelled probes
    end their owned tree before their directory can be removed.
    """
    isolated = dict(env)
    for key in spec.isolated_env_keys:
        isolated[key] = str(directory)
    process = await start_held(
        str(binary), *spec.probe_args, cwd=directory, env=isolated, stdin=asyncio.subprocess.DEVNULL
    )
    assert process.stdout is not None and process.stderr is not None
    readers = (
        asyncio.create_task(_bounded(process.stdout, CATALOGUE_BYTES)),
        asyncio.create_task(_bounded(process.stderr, 65536)),
    )

    async def finish() -> None:
        await stop_or_kill(process, grace_s=1)
        for task in readers:
            task.cancel()
        await asyncio.gather(*readers, return_exceptions=True)

    try:
        async with asyncio.timeout(PROBE_SECONDS):
            stdout, _ = await asyncio.gather(*readers)
            await process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"SDK catalogue probe exited {process.returncode}")
    except TimeoutError as error:
        raise RuntimeError("SDK catalogue probe timed out") from error
    finally:
        _, cancelled = await settle_resources(asyncio.create_task(finish()))
        if cancelled:
            raise asyncio.CancelledError
    try:
        document = json.loads(stdout)
    except (ValueError, UnicodeError) as error:
        raise RuntimeError("SDK catalogue probe returned invalid JSON") from error
    if not isinstance(document, dict):
        raise RuntimeError("SDK catalogue must be a JSON object")
    entries = document.get(spec.entries_at)
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("SDK catalogue must contain nonempty model rows")
    for row in entries:
        if not isinstance(row, dict) or any(
            f.require_present and f.name not in row for f in spec.replace_fields
        ):
            raise RuntimeError("SDK catalogue row lacks a required field")
        for replacement in spec.replace_fields:
            row[replacement.name] = replacement.value
    path = directory / "catalogue.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return spec.config_arg, spec.config_template.replace("{path}", str(path))
