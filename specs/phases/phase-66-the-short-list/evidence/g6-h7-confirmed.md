# H7 — confirmed before implementation, 2026-10-04

Claude Code's provider record advertises native interruption and a measured stream-json control
request, but its dialect has no interrupt_line. JsonlSession.interrupt therefore returns false;
Conversation.interrupt closes that session. BUG-239, P1.

Anthropic's official Python SDK sends a control_request with request_id and a request containing
subtype interrupt. Source checked before implementation:
https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/_internal/query.py

A second boundary matters: Conversation cancels its active run after telling the provider. The
JSONL reader then stops while the CLI's control response and terminal result can still be in the
pipe. Merely adding a line makes the next turn consume the previous result. Test both the shipped
dialect and an explicitly interrupt-capable dialect before fixing, then prove the same process
returns the next turn's own answer. Discard interrupted frames without reporting them into the
next run. Non-native providers keep the close/reopen fallback.

Existing dialect and session contracts suffice: a patch candidate 0.47.2 after 0.47.1. D190:
a coding tool, a support desk and a research assistant would each use interruption that preserves
session identity and turn boundaries. Provider transport, no operation meaning in runtime.

## Verification after implementation

Two cases were red: missing native control request, and old result consumed by the next turn.
Four cases now pass, alongside all 76 JSONL cases. Eight mutations bite, including old thinking and
activity being reported under the new turn. Live measured on Claude Code 2.1.187: interrupt
accepted, same process and session retained, next turn returned SECOND_OK without failure.
Full gate: 2,264 passed, 8 skipped, 24 deselected; lint/format/types clean. Four installed-wheel cases pass outside checkout; all 165 Python package sources and provider record match it. Kit wheel/sdist build and schema/client regeneration has no drift. The live check also passes on the final installed artifact.

A deterministic writer-drain case also proves that a turn finishing before the interrupt call returns clears its pending boundary. All four cases pass on the installed wheel outside checkout.
