"""The run's registry, offered to a child agent — recording as a consequence of routing."""

from shadow_hdk.adapters.recording.pipes import serve_over_pipes
from shadow_hdk.adapters.recording.server import RecordingServer
from shadow_hdk.adapters.recording.socket import (
    PORT_VARIABLE,
    relay,
    serve_over_socket,
)

__all__ = [
    "PORT_VARIABLE",
    "RecordingServer",
    "relay",
    "serve_over_pipes",
    "serve_over_socket",
]
