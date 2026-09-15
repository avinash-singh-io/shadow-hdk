"""Resolve the HTTP bearer without requiring a production secret in process arguments."""

from __future__ import annotations

import os
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path

TOKEN_ENV = "SHADOW_HDK_TOKEN"
MAX_TOKEN_BYTES = 16 * 1024


def resolve_bearer(
    arguments: Sequence[str], *, environ: Mapping[str, str] | None = None
) -> str | None:
    """Resolve token file, environment, then the explicitly local-only argv fallback.

    Every token-file occurrence is parsed before any file is inspected, so an ambiguous command
    cannot disclose which candidate exists or read either secret. File errors name only the path
    and violated property; bearer values never enter an exception.
    """
    token_files = _values(arguments, "token-file")
    if len(token_files) > 1:
        raise ValueError("--token-file was supplied more than once")
    if token_files:
        return _read_private_token(Path(token_files[0]))
    environment = os.environ if environ is None else environ
    if token := environment.get(TOKEN_ENV):
        return _validate_token(token, f"environment variable {TOKEN_ENV}")
    local = _values(arguments, "token")
    return _validate_token(local[0], "local --token flag") if local else None


def _values(arguments: Sequence[str], name: str) -> list[str]:
    values: list[str] = []
    wanted = f"--{name}"
    for index, argument in enumerate(arguments):
        if argument.startswith(f"{wanted}="):
            values.append(argument.split("=", 1)[1])
        elif argument == wanted:
            if index + 1 >= len(arguments) or arguments[index + 1].startswith("--"):
                raise ValueError(f"{wanted} needs a value")
            values.append(arguments[index + 1])
    return values


def _read_private_token(path: Path) -> str:
    shown = str(path)
    try:
        found = path.lstat()
    except OSError as error:
        raise ValueError(f"token file {shown!r} cannot be inspected") from error
    if not stat.S_ISREG(found.st_mode) or path.is_symlink():
        raise ValueError(f"token file {shown!r} must be a regular file, not a link")
    if hasattr(os, "getuid") and found.st_uid != os.getuid():
        raise ValueError(f"token file {shown!r} must be owned by this user")
    if stat.S_IMODE(found.st_mode) & 0o077:
        raise ValueError(f"token file {shown!r} permissions must deny group and other users")
    if found.st_size > MAX_TOKEN_BYTES:
        raise ValueError(f"token file {shown!r} is too large")
    try:
        token = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"token file {shown!r} cannot be read as UTF-8") from error
    if token.endswith("\r\n"):
        token = token[:-2]
    elif token.endswith("\n"):
        token = token[:-1]
    return _validate_token(token, f"token file {shown!r}")


def _validate_token(token: str, source: str) -> str:
    if not token:
        raise ValueError(f"{source} is empty")
    if "\r" in token or "\n" in token:
        raise ValueError(f"{source} must contain one line")
    return token


__all__ = ["MAX_TOKEN_BYTES", "TOKEN_ENV", "resolve_bearer"]
