"""The small real adapters — not doubles, just short."""

from shadow_hdk.adapters.basic.callables import CallableComponents, callable_component
from shadow_hdk.adapters.basic.clock import SystemClock
from shadow_hdk.adapters.basic.governance import AllowAll
from shadow_hdk.adapters.basic.mailbox import Mailbox
from shadow_hdk.adapters.basic.observers import CallbackObserver, StdoutObserver
from shadow_hdk.adapters.basic.sinks import CallbackSink, StdoutSink

__all__ = [
    "AllowAll",
    "CallableComponents",
    "CallbackObserver",
    "CallbackSink",
    "Mailbox",
    "StdoutObserver",
    "StdoutSink",
    "SystemClock",
    "callable_component",
]
