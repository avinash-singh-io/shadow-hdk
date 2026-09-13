"""Shadow HDK — a Harness Development Kit.

A runtime that runs an agent over an open set of components under a governance policy and hands
what the agent produces to whoever is listening. One distribution, one import name:

    shadow_hdk.kernel      pure types and the ports — no I/O, no clock, no framework
    shadow_hdk.runtime     the governed loop, on LangGraph; threads, the environment base
    shadow_hdk.wire        the runtime behind JSON-RPC — stdio, HTTP/SSE — for any language
    shadow_hdk.providers   your key, or your subscription — a provider is a file
    shadow_hdk.serve       the front door: `Harness`, `harness.toml`, `shadow-hdk serve`
    shadow_hdk.adapters    the ports implemented — governance, sinks, components, models, agents

The layering is a test, not a convention: the kernel imports nothing, the runtime imports no
adapter, no adapter imports another, and the wire and the providers import no adapter.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("shadow-hdk")
except PackageNotFoundError:  # pragma: no cover — a source checkout that is not installed
    __version__ = "0"

__all__ = ["__version__"]
