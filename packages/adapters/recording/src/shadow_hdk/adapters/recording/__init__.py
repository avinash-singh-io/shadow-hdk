"""The run's registry, offered to a child agent — recording as a consequence of routing."""

from shadow_hdk.adapters.recording.pipes import serve_over_pipes
from shadow_hdk.adapters.recording.server import RecordingServer

__all__ = ["RecordingServer", "serve_over_pipes"]
