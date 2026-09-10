"""The runtime, reachable from another process or another language."""

from shadow_hdk.wire.channel import Channel, MemoryChannel, channel_pair
from shadow_hdk.wire.peer import Peer, RemoteError
from shadow_hdk.wire.protocol import (
    PROTOCOL_VERSION,
    Agreed,
    VersionMismatch,
    WireError,
)
from shadow_hdk.wire.remote import (
    RemoteComponents,
    RemoteGovernance,
    RemoteModel,
    RemoteSink,
)
from shadow_hdk.wire.sides import HostSide, RuntimeSide, drive, loopback

__all__ = [
    "PROTOCOL_VERSION",
    "Agreed",
    "Channel",
    "HostSide",
    "MemoryChannel",
    "Peer",
    "RemoteComponents",
    "RemoteError",
    "RemoteGovernance",
    "RemoteModel",
    "RemoteSink",
    "RuntimeSide",
    "VersionMismatch",
    "WireError",
    "channel_pair",
    "drive",
    "loopback",
]
