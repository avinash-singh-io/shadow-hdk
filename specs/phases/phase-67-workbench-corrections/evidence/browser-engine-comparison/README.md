# Pinned local browser comparison — 2026-10-13 checkpoint

Archived experiment scripts and raw JSON, not portable installation or release acceptance.
Scripts retain the original `/tmp/hdk67-browser-evaluation` environment paths. No SDK packages,
browser profiles, binaries, credentials or full model catalogues are committed here.

Pins: Playwright 1.63.0 (Apache-2.0), agent-browser 0.39.0 (Apache-2.0), browser-use 0.13.11
(MIT), current unscoped browse 0.11.1 (MIT). The deprecated scoped Browse 0.6.1 was superseded.
Common local fixture, headless Chromium, private profiles/configuration, no model agent loops.
Browser Use telemetry/extensions disabled. Browse uses explicit managed-local operation;
its attempt to attach to the common Chromium timed out, cause unconfirmed.

`comparison.json` records the common probe; `browse-local-comparison.json` records the corrected
managed-local Browse probe (35 references). Compare warm snapshot medians, not CPU totals across
different measurement scopes. Browser Use reports peak Python RSS; the CLIs report daemon RSS;
Chromium and HDK/proxy ownership costs are excluded. These are not energy measurements or
large/real-page performance guarantees. Selection and remaining limitations are in ADR 0001.

The full selected-engine real gate completed before stop: 15 passed, 3 failed, exit 1.
See `../g6-selected-real-controls.txt`. Agent-browser is a selected candidate only; original
Playwright remains the default. Do not switch defaults or claim release acceptance from this probe.

Archived pytest logs remove trailing whitespace only; assertions, outcomes and failures are preserved.
