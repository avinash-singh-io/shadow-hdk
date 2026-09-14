"""Production bearer sources stay out of argv and never disclose their value in a refusal."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.serve.authentication import TOKEN_ENV, resolve_bearer


def test_token_file_precedes_environment_and_local_only_flag(tmp_path: Path) -> None:
    token_file = tmp_path / "bearer"
    token_file.write_text("from-file\n", encoding="utf-8")
    token_file.chmod(0o600)

    resolved = resolve_bearer(
        ["--http", "--token", "from-argv", "--token-file", str(token_file)],
        environ={TOKEN_ENV: "from-env"},
    )

    assert resolved == "from-file"


def test_environment_precedes_the_local_only_flag() -> None:
    assert (
        resolve_bearer(["--http", "--token", "from-argv"], environ={TOKEN_ENV: "from-env"})
        == "from-env"
    )


def test_an_insecure_token_file_is_refused_by_path_without_the_secret(tmp_path: Path) -> None:
    secret = "must-never-be-printed"
    token_file = tmp_path / "bearer"
    token_file.write_text(secret, encoding="utf-8")
    token_file.chmod(0o644)

    with pytest.raises(ValueError) as refused:
        resolve_bearer(["--token-file", str(token_file)], environ={})

    assert str(token_file) in str(refused.value)
    assert "permissions" in str(refused.value)
    assert secret not in str(refused.value)


def test_duplicate_token_file_sources_are_ambiguous_without_reading_either(tmp_path: Path) -> None:
    first = tmp_path / "one"
    second = tmp_path / "two"
    first.write_text("first-secret", encoding="utf-8")
    second.write_text("second-secret", encoding="utf-8")
    os.chmod(first, 0o600)
    os.chmod(second, 0o600)

    with pytest.raises(ValueError, match="token-file.*more than once") as refused:
        resolve_bearer(["--token-file", str(first), "--token-file", str(second)], environ={})
    assert "first-secret" not in str(refused.value)
    assert "second-secret" not in str(refused.value)


def test_a_link_or_multiline_file_is_refused_without_disclosure(tmp_path: Path) -> None:
    token_file = tmp_path / "bearer"
    token_file.write_text("line-one\nline-two", encoding="utf-8")
    token_file.chmod(0o600)
    linked = tmp_path / "linked"
    linked.symlink_to(token_file)

    with pytest.raises(ValueError, match="regular file") as linked_error:
        resolve_bearer(["--token-file", str(linked)], environ={})
    assert "line-one" not in str(linked_error.value)

    with pytest.raises(ValueError, match="one line") as multiline_error:
        resolve_bearer(["--token-file", str(token_file)], environ={})
    assert "line-one" not in str(multiline_error.value)


def test_the_cli_can_take_the_production_bearer_without_putting_it_in_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import anyio

    from shadow_hdk.serve.__main__ import USAGE, main

    secret = "environment-only-secret"
    called: list[tuple[Any, ...]] = []
    monkeypatch.setenv(TOKEN_ENV, secret)
    monkeypatch.setattr(anyio, "run", lambda *args: called.append(args))

    arguments = ["serve", "--http", "--port", "9876"]
    assert main(arguments) == 0
    assert secret not in arguments
    assert called and called[0][3] == secret
    assert "local development only" in USAGE
