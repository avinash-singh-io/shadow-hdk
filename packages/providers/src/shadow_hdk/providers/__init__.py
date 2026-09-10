"""Which model or agent this machine can reach (D39, D41).

Two seams: an **inference** provider a host holds a key for, and an **agent** provider the user
already has a subscription to. This package finds them, asks them about themselves, and hands back
the port — and it **imports no adapter** to do it, which is the whole of its dependency story.
"""

from shadow_hdk.providers.environment import environment_for
from shadow_hdk.providers.library import MalformedProvider, load_dir, load_provider, shipped
from shadow_hdk.providers.probes import Asked, ask_auth, ask_version
from shadow_hdk.providers.resolution import candidates, search_dirs
from shadow_hdk.providers.surface import (
    Available,
    NoSuchTransport,
    detect,
    open_with,
    register_transport,
    transports,
)

__all__ = [
    "Asked",
    "Available",
    "NoSuchTransport",
    "MalformedProvider",
    "ask_auth",
    "ask_version",
    "candidates",
    "detect",
    "environment_for",
    "load_dir",
    "load_provider",
    "open_with",
    "register_transport",
    "search_dirs",
    "shipped",
    "transports",
]
