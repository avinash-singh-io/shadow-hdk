import runpy
m = runpy.run_path('specs/phases/phase-67-workbench-corrections/evidence/check-mutations.py')
check = m['check']
t = 'tests/adapters/browser/test_images_reach_the_model_and_wire.py'
r = 'tests/runtime/test_run_resources.py'
check('g5-model-drops-image', 'src/shadow_hdk/adapters/agent/component.py', 'images=observation.images if isinstance(observation, Completed) else (),', 'images=(),', [t+'::test_images_reach_the_model_and_the_run_closes_resources'])
check('g5-image-becomes-text', 'src/shadow_hdk/adapters/agent/component.py', 'return _as_json(observation.output)', 'return _as_json(observation.output) + "".join(i.data for i in observation.images)', [t+'::test_images_reach_the_model_and_the_run_closes_resources'])
check('g5-child-scopes-diverge', 'src/shadow_hdk/runtime/bindings.py', 'self._resource_scope = resource_owner.resource_scope if resource_owner else session.run_id', 'self._resource_scope = session.run_id', [t+'::test_images_reach_the_model_and_the_run_closes_resources'])
check('g5-no-cleanup', 'src/shadow_hdk/runtime/bindings.py', 'await port.release_run(self.resource_scope)', 'None', [t+'::test_images_reach_the_model_and_the_run_closes_resources', r+'::test_a_cleanup_failure_is_a_failed_run_with_its_reason'])
check('g5-json-drops-images', 'src/shadow_hdk/kernel/observations.py', 'Field(exclude_if=lambda value: not value)', 'Field(exclude=True)', [t+'::test_image_contracts_roundtrip_with_old_empty_defaults'])
check('g5-langchain-drops-images', 'src/shadow_hdk/adapters/langchain/model.py', 'if not message.images:', 'if True:', [t+'::test_langchain_and_mcp_preserve_image_blocks'])
check('g5-mcp-drops-egress-image', 'src/shadow_hdk/adapters/recording/server.py', 'for i in images', 'for i in ()', [t+'::test_langchain_and_mcp_preserve_image_blocks'])
check('g5-mcp-drops-ingress-image', 'src/shadow_hdk/adapters/mcp/components.py', 'if isinstance(b, ImageContent)', 'if isinstance(b, ImageContent) and False', [t+'::test_mcp_image_results_survive_ingress'])
check('g5-cleanup-failure-hidden', 'src/shadow_hdk/runtime/loop.py', 'if cleanup:', 'if False:', [r+'::test_a_cleanup_failure_is_a_failed_run_with_its_reason'])

check('g5-no-model-loop', 'src/shadow_hdk/adapters/agent/component.py', 'return await _Turnwise(self, context).work(brief)', 'return Completed()', [t+'::test_images_reach_the_model_and_the_run_closes_resources'])
check('g5-message-json-drops-images', 'src/shadow_hdk/kernel/ports.py', 'Field(exclude_if=lambda value: not value)', 'Field(exclude=True)', [t+'::test_image_contracts_roundtrip_with_old_empty_defaults'])
w = 'tests/wire/test_images_and_resources.py'
check('g5-wire-drops-scope', 'src/shadow_hdk/wire/remote.py', '"resource_scope": getattr(self._live(), "resource_scope", ""),', '"resource_scope": "",', [w+'::test_crossed_agent_children_share_the_root_resource_scope'])
check('g5-wire-no-cleanup', 'src/shadow_hdk/wire/remote.py', 'await self._peer.call(RELEASE_RUN, {"resource_scope": resource_scope})', 'None', [w+'::test_a_crossed_component_sees_its_resource_scope_and_closes_with_the_run'])
check('g5-wire-no-default', 'src/shadow_hdk/wire/remote.py', 'if error.code != -32601:', 'if True:', [w+'::test_an_older_host_has_the_no_resource_default'])
