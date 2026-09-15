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
    AuthorityPortContract,
    AuthorizerPortContract,
    ClockPortContract,
    ComponentPortContract,
    EffectJournalContract,
    GovernancePortContract,
    ModelPortContract,
    ObserverPortContract,
    QuestionsContract,
    RunStoreContract,
    SinkPortContract,
    StoreContract,
    ThreadStoreContract,
)
from shadow_hdk.testing.providers import ScriptedAgent

__all__ = [
    "AuthorityPortContract",
    "AuthorizerPortContract",
    "ClockPortContract",
    "ComponentPortContract",
    "FixedClock",
    "GovernancePortContract",
    "EffectJournalContract",
    "InMemoryComponents",
    "Judge",
    "ListObserver",
    "ListSink",
    "ModelPortContract",
    "ObserverPortContract",
    "QuestionsContract",
    "RunStoreContract",
    "ScriptedAgent",
    "ScriptedModel",
    "SinkPortContract",
    "StoreContract",
    "ThreadStoreContract",
    "make_registration",
]
