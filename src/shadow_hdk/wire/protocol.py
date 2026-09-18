"""What the two halves agree on before anything else.

`specs/architecture/wire.md`: *negotiated at `initialize`, refusing rather than degrading on a
version mismatch.* Degrading is how two peers come to disagree about what a message means while both
believe they are talking — a class of bug that shows up far from its cause.

The method names are split by direction on purpose. Reading them is meant to answer *who asks whom*,
which is the one thing about this protocol that surprises people: the runtime is the **caller** for
four of them.
"""

from __future__ import annotations

from dataclasses import dataclass

PROTOCOL_VERSION = "3"
"""Bumped when a message's meaning changes. Not the package version: a package may release many
times without the wire's vocabulary moving, and a client generated from published schemas cares
about this number rather than ours."""

# host → runtime
INITIALIZE = "initialize"
RUN = "run"
RESUME = "resume"

# runtime → host — the inversion
JUDGE = "governance.judge"
COMPLETE = "model.complete"
REGISTRATIONS = "components.registrations"
INVOKE = "components.invoke"
PROPOSE = "sink.propose"

# host → runtime, from inside a component the host is running on the runtime's behalf
CONTEXT_PROPOSE = "context.propose"
CONTEXT_REMAINING = "context.remaining"
CONTEXT_REASONING = "context.reasoning"
CONTEXT_VISIBLE = "context.visible"
CONTEXT_FLOOR_MET = "context.floor_met"
CONTEXT_REQUEST_APPROVAL = "context.request_approval"
CONTEXT_REQUEST_INPUT = "context.request_input"
CONTEXT_KEEP = "context.keep"
CONTEXT_ACTIVITY = "context.activity"
CONTEXT_RESUMED = "context.resumed"
CONTEXT_SPAWN = "context.children.spawn"
CONTEXT_SEND = "context.children.send"
CONTEXT_RELEASE = "context.children.release"
CONTEXT_IS_HELD = "context.children.is_held"
"""What a component running on the host asks the run for (D51). Each belongs to the run — the
registry, the meter, the children — and crosses back rather than being answered locally, because
there is one of each and it is on the runtime's side."""

# the thread, crossed (D67) — the host's controls of Phase 25 for a host in any language. The
# runtime side holds the ports in this shape (a `ThreadHost` the serving process hands in).
THREAD_START = "thread/start"
THREAD_RESUME = "thread/resume"
THREAD_CLOSE = "thread/close"
THREAD_LIST = "thread/list"
THREAD_FORK = "thread/fork"
THREAD_ROLLBACK = "thread/rollback"
THREAD_ARCHIVE = "thread/archive"
THREAD_SET_MODE = "thread/set_mode"
THREAD_SET_OPTION = "thread/set_option"
THREAD_REMAINING = "thread/remaining"
THREAD_ADD_ROOT = "thread/add_root"
"""A directory added to the thread's workspace while it runs (D76; Claude Code's `/add-dir`)."""
THREAD_AMEND = "thread/amend"
"""A parked plan continued on a different composition (D116): admitted under the thread's limits
before the run takes it, or refused with every mismatch and the plan untouched."""
TURN_START = "turn/start"
TURN_STEER = "turn/steer"
TURN_INTERRUPT = "turn/interrupt"
# the handles (principle 7): what a person does during a run, from any language
APPROVALS_PENDING = "approvals/pending"
APPROVALS_ANSWER = "approvals/answer"
RUN_CANCEL = "run/cancel"
# the store (D66), crossed
STORE_PUT = "store/put"
STORE_GET = "store/get"
STORE_DELETE = "store/delete"
STORE_LIST = "store/list"
STORE_VERSION = "store/version"
MODES_LIST = "modes/list"
RULES_LIST = "rules/list"
# the thread's workspace, read (D69): what a page shows beside the conversation — under the
# thread's root only, dotfiles and caches left out, never a path that resolves outside it
FILES_LIST = "files/list"
FILES_READ = "files/read"
# the registries a host shows (Phase 28): what the agent is offered now, judged under its mode;
# the skills the composition carries, with their sources
TOOLS_LIST = "tools/list"
SKILLS_LIST = "skills/list"
BATTERIES_LIST = "batteries/list"
"""What the serving process has switched on (D70): every battery it knows, on, off or unavailable
and why."""
PROVIDERS_LIST = "providers/list"
CAPABILITIES_CHECK = "capabilities/check"
# operations (D86): what the process holds, for whoever runs it — behind the bearer
ADMIN_SESSIONS = "admin/sessions"
ADMIN_THREADS = "admin/threads"

# runtime → host, one way
EVENT = "event"
ITEM = "item"
"""The projection, folded runtime-side, one notification per closed step (D46) — so a host in
another language renders agent steps without porting the fold."""
ACTIVITY = "activity"
"""What is happening beside the record (D63), as a notification — never on the record."""
APPROVAL_REQUEST = "approval_request"
INPUT_REQUEST = "input_request"
REQUEST_WITHDRAWN = "request_withdrawn"
"""A request the host must answer, pushed as it becomes pending — and withdrawn when the asker
stopped waiting (D59) — so a client need not poll `approvals/pending`."""

HOST_DRIVES = frozenset({INITIALIZE, RUN, RESUME, CONTEXT_PROPOSE, CONTEXT_REMAINING})
RUNTIME_CALLS_BACK = frozenset({JUDGE, COMPLETE, REGISTRATIONS, INVOKE, PROPOSE})


ERROR_KINDS: tuple[str, ...] = (
    "thread_held",
    "turn_running",
    "capability_mismatch",
    "not_found",
    "invalid",
    "version_mismatch",
    "unknown_method",
    "refused",
    "gone",
    "plan_refused",
)
"""What `error.data.kind` may say (D92) — the vocabulary a client switches on, beside the code
and the sentence. `thread_held` carries `thread_id` and `holder`; `turn_running` carries
`thread_id` and `turn_id`; the rest carry nothing more. `refused` is every other application
*no*; `gone` the other end leaving; `plan_refused` (D108) carries `mismatches` — each with
`axis`, `step`, `required`, `found` — and `amendment`."""


class WireError(Exception):
    """Something the protocol itself refused."""


class VersionMismatch(WireError):
    """`initialize` was offered a version this build does not speak."""


@dataclass(frozen=True)
class Agreed:
    """What `initialize` settled."""

    protocol_version: str


__all__ = [
    "ACTIVITY",
    "APPROVALS_ANSWER",
    "APPROVALS_PENDING",
    "APPROVAL_REQUEST",
    "BATTERIES_LIST",
    "CAPABILITIES_CHECK",
    "INPUT_REQUEST",
    "MODES_LIST",
    "REQUEST_WITHDRAWN",
    "RULES_LIST",
    "RUN_CANCEL",
    "SKILLS_LIST",
    "STORE_DELETE",
    "STORE_GET",
    "STORE_LIST",
    "STORE_PUT",
    "STORE_VERSION",
    "THREAD_ADD_ROOT",
    "THREAD_AMEND",
    "THREAD_ARCHIVE",
    "THREAD_CLOSE",
    "THREAD_FORK",
    "THREAD_LIST",
    "THREAD_REMAINING",
    "THREAD_RESUME",
    "THREAD_ROLLBACK",
    "THREAD_SET_MODE",
    "THREAD_SET_OPTION",
    "THREAD_START",
    "TOOLS_LIST",
    "TURN_INTERRUPT",
    "TURN_START",
    "TURN_STEER",
    "COMPLETE",
    "CONTEXT_PROPOSE",
    "CONTEXT_REMAINING",
    "EVENT",
    "ERROR_KINDS",
    "FILES_LIST",
    "FILES_READ",
    "HOST_DRIVES",
    "INITIALIZE",
    "INVOKE",
    "JUDGE",
    "PROPOSE",
    "PROVIDERS_LIST",
    "PROTOCOL_VERSION",
    "REGISTRATIONS",
    "RESUME",
    "RUN",
    "RUNTIME_CALLS_BACK",
    "Agreed",
    "VersionMismatch",
    "WireError",
]
