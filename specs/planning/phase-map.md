---
type: Plan
status: planned
---

# Phase identities — native foundation and onward

> Effective 2026-09-21. Upcoming work is numbered in the intended reading order from 46.
> **Completed phases, commits, tags, releases and historical evidence are never renumbered.**
> Phase numbers are identities, not versions. Scheduling order comes from overview `deps`.

| Current phase | Name | Previous identity | Depends on | Owner |
|---|---|---|---|---|
| 46 | Architecture proof and contract baseline | New | 45 | Epic 0010 |
| 47 | Native Core and durable execution | New | 46 | Epic 0010 |
| 48 | Components and execution strategies | New | 47 | Epic 0010 |
| 49 | Public APIs and language integration | New | 48 | Epic 0010 |
| 50 | Windows lifecycle and capabilities | Former 43, lifecycle scope | 47 | Epic 0010 |
| 51 | Native distribution | Former 42; native replaces PyApp | 49, 50 | Epic 0010 |
| 52 | Migration and native release acceptance | New; called 50 only in the conversation draft | 51 | Epic 0010 |
| 53 | The harness as data | Former 34 | 52, 36 | Epic 0009 |
| 54 | The durable run request | Former 37 | 53 | Epic 0009 |
| 55 | Context engineering | Former 35 | 54 | Later roadmap |
| 56 | The UI plane | Former 38 | 54 | Later roadmap |
| 57 | Collaboration | Former 39 | 54 | Later roadmap |
| 58 | Evaluation and governed evolution | Former 40 | 55 | Later roadmap |

Phase 50 may technically run after 47; numerical order is not a false dependency on 49.
The later-capability dependency on 54 records the owner's sequencing after native foundation
and Epic 0009, not a technical claim that UI, memory or peer protocols require a scheduler.

## Historical aliases and scope

Old **planned** IDs 34, 35, 37, 38, 39, 40, 42 and 43 are retired, not reassigned. They remain
valid historical references through this map. No corresponding phase directories existed when
this mapping was made, so there were no old task/history files to move. Completed 36, 41, 44 and
45 retain their identities even though execution previously happened out of numeric order.

Former 43 also included native Windows confinement hardening. That unfinished scope is explicitly
deferred beyond Phase 50; it has not been completed or erased. Phase 50 must supervise Windows
processes and refuse unsupported requested isolation. A future hardening phase needs its own
evidence-backed design. Former 42's mandatory embedded-Python artifact approach is superseded.

Current roadmap tables, epic membership and phase overview metadata use new IDs. Old dated
research, completed history, release notes and retrospective statements keep their original IDs.
External ecosystem references must be remapped by their owning session, not rewritten here.

## Execution boundary

These are planned overviews, not started phases or speculative detailed task plans. Phase 46 is
the next implementation candidate. Public release versions are chosen at contract/release gates,
not inferred from these phase numbers. Ready-made Shadow applications remain lower priority.
