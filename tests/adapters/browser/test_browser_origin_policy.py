"""Origins are host configuration; navigation data cannot widen them."""

import pytest

from shadow_hdk.adapters.browser.policy import OriginPolicy


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:3000/app",
        "http://127.0.0.1:8080/",
        "https://[::1]:9000/",
    ],
)
def test_default_policy_permits_loopback(url: str) -> None:
    assert OriginPolicy().allows(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/",
        "http://localhost.example.com/",
        "file:///etc/passwd",
        "data:text/html,hello",
        "ftp://localhost/x",
        "http://user:secret@localhost/",
        "http://0.0.0.0/",
        "http://169.254.169.254/",
        "javascript:alert(1)",
    ],
)
def test_default_policy_denies_other_origins_and_unsafe_urls(url: str) -> None:
    assert not OriginPolicy().allows(url)


def test_approved_origins_match_scheme_host_and_effective_port() -> None:
    policy = OriginPolicy(origins=("https://Example.com:443",), allow_localhost=False)
    assert [
        policy.allows(url)
        for url in (
            "https://example.com/app",
            "https://example.com:444/app",
            "http://example.com/app",
            "https://sub.example.com/",
            "http://localhost/",
        )
    ] == [True, False, False, False, False]


@pytest.mark.parametrize(
    "origin",
    [
        "http://user:secret@localhost",
        "http://localhost/path",
        "http://localhost/?x=y",
        "http://localhost/#part",
        "file:///tmp",
        "https://example.com:99999",
        "http://localhost:0",
        "http://[broken",
    ],
)
def test_configuration_requires_an_origin_without_credentials_or_paths(origin: str) -> None:
    with pytest.raises(ValueError, match="origin"):
        OriginPolicy(origins=(origin,))
