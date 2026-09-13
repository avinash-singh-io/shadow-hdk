"""What a product tests its harness with (D91): the contract suites every port is held to, and
doubles — a scripted provider, the runtime's fakes — so a product's tests reach no model, no
CLI and no network. `shadow_hdk.runtime.testing` keeps the runtime's own doubles; this package
is the front door for a product."""

from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    Judge,
    ListObserver,
    ListSink,
    ScriptedModel,
    make_registration,
)
from shadow_hdk.testing.contracts import (
    ClockPortContract,
    ComponentPortContract,
    GovernancePortContract,
    ModelPortContract,
    ObserverPortContract,
    QuestionsContract,
    SinkPortContract,
    StoreContract,
    ThreadStoreContract,
)
from shadow_hdk.testing.providers import ScriptedAgent

__all__ = [
    "ClockPortContract",
    "ComponentPortContract",
    "FixedClock",
    "GovernancePortContract",
    "InMemoryComponents",
    "Judge",
    "ListObserver",
    "ListSink",
    "ModelPortContract",
    "ObserverPortContract",
    "QuestionsContract",
    "ScriptedAgent",
    "ScriptedModel",
    "SinkPortContract",
    "StoreContract",
    "ThreadStoreContract",
    "make_registration",
]
