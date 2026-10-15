"""An immutable host allowlist. Browser actions cannot grant themselves network origins."""

from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import urlsplit


def _origin(url: str) -> tuple[str, str, int] | None:
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
        if port < 1:
            return None
        return parsed.scheme, host, port
    except (ValueError, UnicodeError):
        return None


@dataclass(frozen=True)
class OriginPolicy:
    """Localhost only by default, plus exact origins explicitly supplied by the host."""

    origins: tuple[str, ...] = ()
    allow_localhost: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "origins", tuple(self.origins))
        for origin in self.origins:
            try:
                parsed = urlsplit(origin)
            except ValueError as error:
                raise ValueError(f"invalid browser origin: {origin!r}") from error
            if (
                _origin(origin) is None
                or parsed.path not in ("", "/")
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    f"expected an HTTP(S) origin without credentials or a path: {origin!r}"
                )

    def allows(self, url: str) -> bool:
        origin = _origin(url)
        if origin is None:
            return False
        if origin in {_origin(approved) for approved in self.origins}:
            return True
        if not self.allow_localhost:
            return False
        host = origin[1]
        if host == "localhost":
            return True
        try:
            return ip_address(host).is_loopback
        except ValueError:
            return False
