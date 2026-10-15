# Group 5 — resource lifetime follows its owner

The original candidate cleaned up each execution leg. New controls failed because a parked run had already released its resources, and a Thread's first turn released its scope before the second turn. The ADR is corrected before browser implementation.

- `RunOptions.resource_scope=None`: the root owns teardown; park retains resources, resume on the same run ID releases them when it ends. Children share the root scope.
- A host supplies an opaque scope to retain resources across low-level runs; the host releases its resource ports when finished. This ownership choice crosses both wire run and resume.
- Conversation/Thread supply their own identity across turns and parked approval settlement, and release their composed resource ports once on close. Aliases are deduplicated; every port is attempted after a failure. Additional ports introduced in child compositions within a host-owned scope remain the host's responsibility.
- Close settles resource teardown before delivering caller cancellation. Thread settles its store-hold release too, even after repeated cancellation or teardown failure (BUG-241).
- Browser state is process-local. It can survive a pause while the owner remains alive; a durable checkpoint does not preserve a browser process after host restart. Closing the scope deliberately invalidates its resources.

Evidence:

- `g5-lifetime-red.txt`: 2 assertion failures (early park cleanup and turn cleanup).
- `g5-thread-close-red.txt`: 2 assertion failures (leaked hold on cancellation/failure).
- `g5-repeated-close-red.txt`: 1 assertion failure (second cancellation interrupted hold release).
- 13 mutations all bite, source restored exactly. Each `g5-lifetime-mutant-*.txt` identifies the intended behavioral failure. `g5-lifetime-restored-control.txt`: 14 passed.
- `g5-lifetime-regressions.txt`: 225 passed, covering wire, conversation, parked turns/restart and key-backed multi-turn behavior.
- `g5-lifetime-types.txt`: strict mypy passes 512 source files; fresh lint and formatting pass for src/tests.

The browser component, workbench packs, Codex read restriction and publication remain pending. This is candidate evidence, not a release claim.
