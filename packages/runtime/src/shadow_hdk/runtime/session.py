"""What one run holds while it is alive: its handles, and its meter.

Nothing here outlives the run. That is deliberate (`09` §6): a runtime that persists its own state
is a runtime that cannot be replaced.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import JsonValue

from shadow_hdk.kernel.components import Registration
from shadow_hdk.kernel.composition import StepId
from shadow_hdk.kernel.events import EndReason, RunId
from shadow_hdk.kernel.leases import Ceiling, Floor, Lease
from shadow_hdk.kernel.ports import ClockPort, Context, Usage
from shadow_hdk.runtime.cancel import Cancellation


class LeaseMeter:
    """The ceiling, the floor, and what has been spent — including what children hold.

    A child's ceiling is **carved** from what is left, never added to it, so fan-out changes shape
    and never the total. The ceiling always beats the floor; the ceiling is someone's money.
    """

    def __init__(self, lease: Lease, clock: ClockPort) -> None:
        self._lease = lease
        self._clock = clock
        self._started = datetime.fromisoformat(clock.now())
        self._steps = 0
        self._cost = 0
        self._cost_known = True
        self._carved_steps = 0
        self._carved_cost = 0

    @property
    def lease(self) -> Lease:
        return self._lease

    @property
    def steps(self) -> int:
        return self._steps

    @property
    def cost_cents(self) -> int:
        """What has been spent *and priced*. Never a stand-in for what could not be priced."""
        return self._cost

    @property
    def cost_is_known(self) -> bool:
        """False once a model call arrived whose price the provider would not report."""
        return self._cost_known

    def charge(self, usage: Usage | None = None) -> None:
        """Count a step, and its cost if there was one.

        ``usage=None`` means *this step made no model call* — no cost, and that is known.
        ``Usage(..., cost_cents=None)`` means *a model call nobody could price* — unknown, which is
        not zero, and the meter stops claiming to know the total.
        """
        self._steps += 1
        self.charge_cost(usage)

    def charge_cost(self, usage: Usage | None) -> None:
        """Price a step that has already been counted.

        A step is counted when it **begins**, so a step in flight tells against the ceiling and
        concurrent children cannot collectively overrun it. What it cost can only be known when it
        **ends** — so the two are charged at different moments, and this is the second one.
        """
        if usage is None:
            return
        if usage.cost_cents is None:
            self._cost_known = False
        else:
            self._cost += usage.cost_cents

    def elapsed_seconds(self) -> float:
        return (datetime.fromisoformat(self._clock.now()) - self._started).total_seconds()

    def check(self) -> EndReason | None:
        """Called before every step. `None` means go ahead."""
        ceiling = self._lease.ceiling
        if self._steps + self._carved_steps >= ceiling.max_steps:
            return "lease_exhausted"
        if self.elapsed_seconds() >= ceiling.max_wall_seconds:
            return "lease_exhausted"
        if ceiling.max_cost_cents is not None and (
            self._cost + self._carved_cost >= ceiling.max_cost_cents
        ):
            return "lease_exhausted"
        return None

    def floor_met(self) -> bool:
        """Has the agent done enough to be allowed to say it cannot finish?"""
        return self._steps >= self._lease.floor.min_steps

    def remaining(self) -> Lease:
        ceiling = self._lease.ceiling
        cost: int | None = None
        if ceiling.max_cost_cents is not None and self._cost_known:
            cost = max(0, ceiling.max_cost_cents - self._cost - self._carved_cost)
        left = Ceiling(
            max_steps=max(0, ceiling.max_steps - self._steps - self._carved_steps),
            max_wall_seconds=max(0, int(ceiling.max_wall_seconds - self.elapsed_seconds())),
            max_cost_cents=cost,
        )
        return Lease(left, Floor(min(self._lease.floor.min_steps, left.max_steps)))

    def carve(self, child: Ceiling) -> Lease:
        """**Reserve** part of what is left for a child. Raises if it would exceed it.

        A reservation is not a spend. It holds the child's worst case so two concurrent children
        cannot both be promised the same budget — and it must be released by `settle` when the child
        ends, or an agent running twelve turns would drain its parent with money nobody used.
        """
        child_lease, _ = self.remaining().carve(child)
        self._carved_steps += child.max_steps
        self._carved_cost += child.max_cost_cents or 0
        return child_lease

    def settle(self, reserved: Ceiling, *, steps: int, cost_cents: int, cost_known: bool) -> None:
        """Release a child's reservation and charge what it actually spent.

        Always paired with `carve`, and called by the drive when a child run ends — including when
        it ends badly, because a reservation held by a run that has stopped is money lost to
        nobody.
        """
        self._carved_steps -= reserved.max_steps
        self._carved_cost -= reserved.max_cost_cents or 0
        self._steps += steps
        if cost_known:
            self._cost += cost_cents
        else:
            self._cost_known = False


class Session:
    """One run's identity, handles and meter."""

    def __init__(
        self,
        *,
        run_id: RunId,
        lease: Lease,
        clock: ClockPort,
        context: dict[str, JsonValue] | None = None,
        principal: str | None = None,
        parent_run_id: RunId | None = None,
        cancellation: Cancellation | None = None,
    ) -> None:
        self.run_id = run_id
        self.parent_run_id = parent_run_id
        self.principal = principal
        self.meter = LeaseMeter(lease, clock)
        self.cancellation = cancellation if cancellation is not None else Cancellation()
        self._context = dict(context or {})

    def context_for(self, step: StepId, registration: Registration | None = None) -> Context:
        """What governance is told. Opaque to the runtime; the adapter interprets it.

        With a registration, the policy is also told **what** it is judging: the component's id
        and its posture (D30), so *only controlled satisfies consent-before-effect* is a rule a
        policy can enforce rather than a sentence in a document.
        """
        attributes: dict[str, JsonValue] = dict(self._context)
        if registration is not None:
            attributes["posture"] = registration.component.provenance.posture
            attributes["component"] = registration.id
        return Context(
            run_id=self.run_id,
            step=step,
            principal=self.principal,
            attributes=attributes,
        )
