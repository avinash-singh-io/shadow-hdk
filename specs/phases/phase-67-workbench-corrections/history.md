# History

## 2026-10-13
- [DECISION] Owner approved all four corrections and proper release, following the recommendation as 0.48.0. This is advance authorization for staging → main, tag, GitHub release and PyPI publication.
- [DISCOVERY] Runtime proof: SocketOffer is not Narrowing, its holder is. Existing tests exercise Routing/RecordingServer and miss the production wrapper.
- [DECISION] Preserve tracked files under Git ignore semantics; use exact ownership for custom branches. Existing environment mechanisms remain maintenance-only under D190.
- [START] Group 0 complete. Phase 67 and v0.48.0 claimed. Starting N-W0 red proof.

- [VERIFY] Group 1: production socket/relay mode-switch regression plus existing controls, 10 passed. Removing forwarding kills both catalogue/call and execution assertions; source restored byte-for-byte, 2 restored controls pass.
- [DISCOVERY] okf index regeneration removed curated decision records; restored the prior curated indexes rather than accepting that unrelated deletion.
