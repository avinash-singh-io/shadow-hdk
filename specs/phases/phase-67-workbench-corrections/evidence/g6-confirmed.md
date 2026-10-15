# Browser candidate — verified, not published

The restored source passes 41 controls, including a real first-use download, private cookies,
multi-tab operations, accessibility/interaction/rendered screenshots, console and failed requests,
multi-turn image delivery, HTTP status, TLS verification, cleanup and refusal after scope close.
`g6-restored.txt` records this run. `g6-mutants.txt` records 32 behavioural mutants, all detected
with exact source restoration; all 14 original image/wire mutants were rechecked in
`g5-current-mutants.txt`. Strict types pass across 531 source/test files; lint/format pass.

Denied HTTP and TLS servers receive neither requests nor TCP connections across redirects,
images, fetches, dedicated workers and WebSockets. An allowed TLS server and socket work.
An untrusted upstream certificate yields a visible HTTP 502 without an application request.
The WebRTC control first proves an unconstrained Chromium sends STUN packets, then observes
zero packets from the governed engine; deleting its UDP restriction breaks that assertion.

Deleting the explicit loopback bypass argument alone survives because Playwright also supplies
that restriction. Altering a proxy bypass alone likewise survives that explicit argument. These
redundant controls are not counted as detected mutants. Removing the proxy itself breaks the
HTTP subresource pre-connection assertion; removing exact scheme checks contacts the denied
TLS server even though HTTP on its authority is approved. This separates redundancy from a
missing feature assertion.

An installed base wheel outside the checkout has no Playwright or uv, exposes all 17
registrations, carries the gateway code resource, and explicitly reports the missing extra.
The wheel/sdist build succeeds (`g6-build.txt`). SDK dependencies are isolated because
mitmproxy's Python 3.12 dependency bounds conflict with Pydantic 2.12; no upstream constraints
were overridden. The real controls use the default pinned SDK provisioner.

Initial controls also caught three session leaders started outside the shared ownership helper;
all three now use `start_held`, and the invariant plus cancelled-installer controls pass.

Final release acceptance still needs exact-head CI, the whole expanded phase's full gate,
versioned packages, publication and fresh installs. 0.47.3 remains latest published.
