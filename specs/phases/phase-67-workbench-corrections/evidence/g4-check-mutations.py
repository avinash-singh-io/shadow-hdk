import runpy
m = runpy.run_path('specs/phases/phase-67-workbench-corrections/evidence/check-mutations.py')
check = m['check']
f = 'src/shadow_hdk/adapters/environment/history.py'
t = 'tests/adapters/environment/test_history_reuses_work_and_preserves_state.py'
check('g4-rewrite-stable', f, 'await self._git("read-tree", "-m", commit, index=index)\n            checkout = [p for p in changed if p in held]', 'await self._git("read-tree", commit, index=index)\n            checkout = [p for p in held if p]', [t+'::test_restore_does_not_rewrite_unchanged_files_or_walk_ignored_folders'])
check('g4-walk-ignored', f, 'emptied: set[Path] = set()', 'emptied: set[Path] = set()\n            list(self.root.rglob("*"))', [t+'::test_restore_does_not_rewrite_unchanged_files_or_walk_ignored_folders'])
check('g4-keep-empty-directories', f, 'where.rmdir()', 'None', [t+'::test_restore_does_not_rewrite_unchanged_files_or_walk_ignored_folders'])
check('g4-new-private-index', f, 'tree = await self._capture(str(state / "index"))', 'tree = await self._capture(str(state / uuid.uuid4().hex))', [t+'::test_snapshots_reuse_a_private_index_across_instances_and_capture_external_edits'])
check('g4-no-external-capture', f, 'await self._git("add", "-A", index=index)', 'None', [t+'::test_snapshots_reuse_a_private_index_across_instances_and_capture_external_edits', t+'::test_tracked_ignored_files_and_file_modes_are_restored_without_touching_git'])
check('g4-change-person-index', f, 'await self._git("read-tree", "-m", commit, index=index)', 'await self._git("read-tree", "-m", commit, index=index)\n            await self._git("read-tree", commit)', [t+'::test_tracked_ignored_files_and_file_modes_are_restored_without_touching_git'])
check('g4-keep-ignored-cache', f, 'removed = cached - eligible', 'removed = set()', [t+'::test_newly_ignored_untracked_content_is_not_kept_by_the_cache'])
check('g4-no-lock', f, 'async with AsyncFileLock(str(state / "operation.lock"), timeout=60):\n            tree', 'async with __import__("contextlib").nullcontext():\n            tree', [t+'::test_concurrent_history_instances_serialize_and_restart_after_cache_loss'])
