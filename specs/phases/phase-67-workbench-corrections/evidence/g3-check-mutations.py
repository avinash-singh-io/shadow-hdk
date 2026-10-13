import runpy
m = runpy.run_path('specs/phases/phase-67-workbench-corrections/evidence/check-mutations.py')
check = m['check']
f = 'src/shadow_hdk/runtime/environment.py'
l = 'src/shadow_hdk/adapters/environment/local.py'
t = 'tests/adapters/environment/test_search_honours_ignores.py'
check('g3-ignore-rules', f, 'excluded = checked.include', 'excluded = False', [t+'::test_nested_ignore_and_negation[asyncio-glob-False]', t+'::test_nested_ignore_and_negation[asyncio-grep-False]', t+'::test_portable_search_never_lists_an_ignored_directory', t+'::test_starting_below_root_still_applies_ancestor_ignores'])
check('g3-git-unignored', l, '"--exclude-standard",', '"--exclude-standard", "--ignored",', [t+'::test_nested_ignore_and_negation[asyncio-glob-True]', t+'::test_nested_ignore_and_negation[asyncio-grep-True]', t+'::test_tracked_ignored_files_remain_searchable_and_metadata_does_not'])
check('g3-ceiling', f, 'while pending:\n            here, inherited', 'while pending:\n            if len(found) >= 50_000:\n                break\n            here, inherited', [t+'::test_portable_search_has_no_silent_repository_ceiling'])
check('g3-escape', l, 'except (OutsideTheRoot, ValueError, OSError):\n                    continue\n            found.append', 'except (OutsideTheRoot, ValueError, OSError):\n                    pass\n            found.append', [t+'::test_non_git_search_does_not_follow_directory_cycles_or_escape'])
