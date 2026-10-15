import os
import runpy

os.environ['SHADOW_HDK_TEST_CODEX'] = '1'
check = runpy.run_path('specs/phases/phase-67-workbench-corrections/evidence/check-mutations.py')['check']
t = 'tests/adapters/jsonl/test_governed_cli_bootstrap.py'
r = 'tests/adapters/jsonl/test_real_codex_governance.py'
s = 'src/shadow_hdk/adapters/jsonl/session.py'
p = 'src/shadow_hdk/providers/library/codex.toml'
check('g8-private-launch-disabled', s, 'if self._tools and self._dialect.private_working_directory:', 'if False:', [t+'::test_private_bootstrap_survives_turns_then_closes_even_after_process_exit'])
check('g8-uninjected-launch-changed', s, 'if self._tools and self._dialect.private_working_directory:', 'if self._dialect.private_working_directory:', [t+'::test_an_uninjected_cli_keeps_its_working_directory'])
check('g8-private-launch-not-cleaned', s, 'self._private_workspace.cleanup()\n                self._private_workspace = None', 'None', [t+'::test_private_bootstrap_survives_turns_then_closes_even_after_process_exit'])
check('g8-shell-enabled', p, '"--disable", "shell_tool",', '"--enable", "shell_tool",', [r])
check('g8-native-image-enabled', p, '"--disable", "view_image",', '"--enable", "view_image",', [r])
check('g8-repository-discovery-restored', p, 'private_working_directory = true', 'private_working_directory = false', [r])
check('g8-tool-capability-false', p, 'tool_path = "controlled"', 'tool_path = "uncontrolled"', ['tests/providers/test_library.py::test_shipped_capabilities_say_only_what_the_measurements_support'])

check('g8-close-not-settled', s, '_, cancelled = await settle_resources(asyncio.create_task(self._close()))', 'await self._close()\n        cancelled = False', [t+'::test_cancelled_close_settles_before_removing_the_private_directory'])
