"""The one design decision (09 §2): govern effects, not names.

A component's name is open. What it does to the world is declared in six fields, each with a
natural "narrower than" order, so intersection and the narrowing proof work over them however many
components exist. The vocabulary may grow by one shape only — a scope-set or a boolean — never a
predicate, because a predicate turns a proof into a linter.

The order, per field, reads *safer is smaller*:

    reads, writes   ⊆  on scope-sets
    reaches         False < True
    reversible      True  < False      (irreversible is the wider effect)
    contained       True  < False      (uncontained is the wider effect)
    costs           False < True
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

Scope = str
"""An open set of names — ``session``, ``host``, ``workspace``, ``network`` … The kernel never
enumerates them; the governance adapter knows which exist on a deployment."""


@dataclass(frozen=True)
class ScopeSet:
    """A set of scopes that can also honestly say *everything*.

    A component that will not declare what it reads or writes is registered as touching everything
    (09 §2: a missing declaration means assume the worst, never assume nothing), and "everything"
    over an open set of names cannot be spelled as a list.
    """

    names: frozenset[Scope] = frozenset()
    everything: bool = False

    def __le__(self, other: ScopeSet) -> bool:
        if other.everything:
            return True
        if self.everything:
            return False
        return self.names <= other.names

    def __and__(self, other: ScopeSet) -> ScopeSet:
        if self.everything:
            return other
        if other.everything:
            return self
        return ScopeSet(self.names & other.names)

    def __contains__(self, scope: Scope) -> bool:
        return self.everything or scope in self.names

    @classmethod
    def of(cls, *names: Scope) -> ScopeSet:
        return cls(frozenset(names))


EVERYTHING: Final = ScopeSet(everything=True)
NO_SCOPES: Final = ScopeSet()


@dataclass(frozen=True)
class EffectProfile:
    """Six fields. Names open, effects closed."""

    reads: ScopeSet = NO_SCOPES
    writes: ScopeSet = NO_SCOPES
    reaches: bool = False
    reversible: bool = True
    contained: bool = True
    costs: bool = False

    def narrows(self, other: EffectProfile) -> bool:
        """True iff every field of ``self`` is at most as wide as ``other``'s.

        This is the whole narrowing proof: a mode narrows a base iff its ceiling profile narrows
        the base's; a component is visible under a ceiling iff its profile narrows it.
        """
        return (
            self.reads <= other.reads
            and self.writes <= other.writes
            and (other.reaches or not self.reaches)
            and (self.reversible or not other.reversible)
            and (self.contained or not other.contained)
            and (other.costs or not self.costs)
        )

    def meet(self, other: EffectProfile) -> EffectProfile:
        """The greatest profile narrower than both — how two ceilings compose.

        Composition by meet is what makes "a team mode may only narrow" a property rather than a
        review: ``a.meet(b)`` narrows ``a`` and narrows ``b`` by construction, and any profile that
        narrows both narrows the meet.
        """
        return EffectProfile(
            reads=self.reads & other.reads,
            writes=self.writes & other.writes,
            reaches=self.reaches and other.reaches,
            reversible=self.reversible or other.reversible,
            contained=self.contained or other.contained,
            costs=self.costs and other.costs,
        )

    @classmethod
    def from_mcp_annotations(
        cls,
        *,
        read_only_hint: bool | None = None,
        destructive_hint: bool | None = None,
        idempotent_hint: bool | None = None,
        open_world_hint: bool | None = None,
    ) -> EffectProfile:
        """Half a profile from what MCP already declares; the rest assumes the worst.

        MCP's own defaults apply where a hint is absent: not read-only, destructive, open-world.
        ``idempotent_hint`` is accepted so an adapter can pass the whole annotation block, but it
        names no effect in this vocabulary and is ignored. Nothing here is trusted for the fields
        that matter most — ``contained`` and ``costs`` stay at their worst until the deployment or
        a signed registration says otherwise.
        """
        read_only = bool(read_only_hint)
        destructive = True if destructive_hint is None else destructive_hint
        open_world = True if open_world_hint is None else open_world_hint
        return cls(
            reads=EVERYTHING,
            writes=NO_SCOPES if read_only else EVERYTHING,
            reaches=open_world,
            reversible=read_only or not destructive,
            contained=False,
            costs=True,
        )


NOTHING: Final = EffectProfile()
"""The bottom of the order: reads and writes nothing, reaches nothing; reversible, contained,
free."""

ASSUME_WORST: Final = EffectProfile(
    reads=EVERYTHING,
    writes=EVERYTHING,
    reaches=True,
    reversible=False,
    contained=False,
    costs=True,
)
"""The top of the order, and the profile of anything that declines to declare one."""
