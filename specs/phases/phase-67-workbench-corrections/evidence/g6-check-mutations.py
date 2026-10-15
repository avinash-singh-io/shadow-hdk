"""Browser counterfactuals, including real HTTP/TLS/socket/UDP endpoints."""
import os
import runpy

anchored = runpy.run_path('specs/phases/phase-67-workbench-corrections/evidence/check-mutations.py')['check']
started = not os.environ.get('G6_FROM')
def check(label, *args):
    global started
    started = started or label == os.environ.get('G6_FROM')
    if started:
        anchored(label, *args)

os.environ['SHADOW_HDK_BROWSER_TESTS'] = '1'
root = 'src/shadow_hdk/adapters/browser/'
test = 'tests/adapters/browser/'
policy = [test + 'test_browser_origin_policy.py']
inputs = [test + 'test_browser_inputs_match_the_catalogue.py']
edit = [test + 'test_real_browser.py::test_edit_navigate_debug_and_take_real_images']
origins = [test + 'test_real_browser.py::test_redirects_subresources_workers_and_websockets_cannot_reach_denied_origins']
provision = [test + 'test_browser_provisioning_and_cleanup.py']
check('g6-no-loopback', root+'policy.py', 'return ip_address(host).is_loopback', 'return False', policy)
check('g6-host-prefix-grant', root+'policy.py', 'if host == "localhost":', 'if host.startswith("localhost"):', policy)
check('g6-ignore-localhost-disabled', root+'policy.py', 'if not self.allow_localhost:', 'if False:', policy)
check('g6-ignore-origin-port', root+'policy.py', 'if origin in {_origin(approved) for approved in self.origins}:',
      'if origin[:2] in {value[:2] for approved in self.origins if (value := _origin(approved)) is not None}:', policy)
check('g6-ignore-origin-path', root+'policy.py', 'or parsed.path not in ("", "/")', 'or False', policy)
check('g6-ignore-origin-query', root+'policy.py', 'or parsed.query', 'or False', policy)
check('g6-ignore-origin-fragment', root+'policy.py', 'or parsed.fragment', 'or False', policy)
check('g6-null-accepted', root+'arguments.py', 'if any(value is None for value in inputs.values()):', 'if False:', inputs)
check('g6-ignored-fields-accepted', root+'arguments.py', 'inputs.keys() - FIELDS[action]', 'False', inputs)
check('g6-name-ignored', root+'arguments.py', 'if params.name is not None and not params.role:', 'if False:', inputs)
check('g6-schema-drops-required', root+'arguments.py', '[REQUIRED[action]] if action in REQUIRED else []', '[]', inputs)
check('g6-schema-drops-limits', root+'arguments.py', 'properties[name] = cast(JsonValue, prop)',
      'properties[name] = {"type": prop["type"]}', inputs)
check('g6-no-fill', root+'engine.py', 'await locator.fill(params.value)', 'None', edit)
check('g6-no-select', root+'engine.py', 'await locator.select_option(params.values)', 'None', edit)
check('g6-no-scroll', root+'engine.py', 'await page.mouse.wheel(params.x, params.y)', 'None', edit)
check('g6-false-find-count', root+'engine.py', 'count = await locator.count()\n            matches:', 'count = 0\n            matches:', edit)
check('g6-false-image', root+'engine.py', 'base64.b64encode(png).decode()', 'base64.b64encode(b"not an image").decode()', edit)
check('g6-drop-tab', root+'engine.py', 'identity = f"tab-{self.next_tab}"', 'identity = "tab-1"', edit)
check('g6-closed-tab-retained', root+'engine.py', 'await page.close()', 'None', edit)
check('g6-console-ignored-filter', root+'engine.py', 'if params.tab is None\n                or (isinstance(entry, dict) and entry.get("tab") == params.tab)', 'if True', edit)
check('g6-console-discarded', root+'engine.py', '"text": message.text[:8000]', '"text": ""', edit)
check('g6-http-failures-discarded', root+'engine.py', 'if response.status >= 400', 'if False', edit)
check('g6-navigation-status-dropped', root+'engine.py', 'output["status"] = response.status if response is not None else None', 'output["status"] = None',
      [test+'test_real_browser.py::test_navigation_reports_http_failures_and_preserves_upstream_tls_verification'])
check('g6-scheme-boundary-dropped', root+'mitm_addon.py.template', 'if not self.policy.allows(flow.request.url):', 'if False:', origins)
check('g6-localhost-proxy-bypass', root+'engine.py',
      'proxy={"server": f"http://127.0.0.1:{profile.gateway.port}"},', '',
      [test+'test_real_browser.py::test_http_subresource_denial_precedes_a_connection'])
check('g6-webrtc-bypass', root+'engine.py', '"--force-webrtc-ip-handling-policy=disable_non_proxied_udp",', '',
      [test+'test_real_browser.py::test_page_webrtc_does_not_contact_an_unapproved_udp_server'])
check('g6-cookie-profile-shared', root+'engine.py', 'profile = self._profiles.get(resource_scope)',
      'profile = next(iter(self._profiles.values()), None)',
      [test+'test_real_browser.py::test_overlapping_runs_have_isolated_cookies_and_close_independently'])
check('g6-driver-not-closed-on-failure', root+'engine.py', '(self.driver, "stop"),', '', provision)
check('g6-install-message-dropped', root+'engine.py', '"install", "Installing Chromium for the optional browser component."',
      '"install", ""', provision)
check('g6-closed-scope-reopened', root+'engine.py', 'if resource_scope in self._closed:', 'if False:', edit)
image = [test+'test_tool_images_fit_native_chat_protocols.py']
check('g6-image-carrier-early', 'src/shadow_hdk/adapters/langchain/model.py', 'if message.role != "tool" and images:', 'if images:', image)
check('g6-image-source-lost', 'src/shadow_hdk/adapters/langchain/model.py', 'f"Images returned by tool call {message.tool_call_id}."', '"Images returned by a tool."', image)
