"""Production bearer sources stay out of argv and never disclose their value in a refusal."""

from __future__ import annotations

import os
from pathlib import Path

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
