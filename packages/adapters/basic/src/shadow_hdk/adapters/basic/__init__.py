"""The small real adapters — not doubles, just short."""

from shadow_hdk.adapters.basic.callables import CallableComponents, callable_component
from shadow_hdk.adapters.basic.clock import SystemClock
from shadow_hdk.adapters.basic.governance import AllowAll, Controlled
from shadow_hdk.adapters.basic.mailbox import Mailbox
from shadow_hdk.adapters.basic.observers import CallbackObserver, StdoutObserver
from shadow_hdk.adapters.basic.sinks import CallbackSink, FileSink, StdoutSink, proposals_in
from shadow_hdk.adapters.basic.store import SqliteStore
from shadow_hdk.adapters.basic.threads import SqliteThreads

__all__ = [
    "Controlled",
    "FileSink",
    "proposals_in",
    "AllowAll",
    "CallableComponents",
    "CallbackObserver",
    "CallbackSink",
    "Mailbox",
    "StdoutObserver",
    "SqliteStore",
    "SqliteThreads",
    "StdoutSink",
    "SystemClock",
    "callable_component",
]
