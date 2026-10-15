import runpy
m = runpy.run_path('specs/phases/phase-67-workbench-corrections/evidence/check-mutations.py')
check = m['check']
f = 'src/shadow_hdk/adapters/environment/worktrees.py'
t = 'tests/adapters/environment/test_the_host_names_its_branch.py'
check('g2-ignore-host-branch', f, 'branch = f"{BRANCHES}/{name}" if branch is None else branch', 'branch = f"{BRANCHES}/{name}"', [t+'::test_custom_branch_lifecycle[asyncio-branch]', t+'::test_custom_branch_lifecycle[asyncio-head]', t+'::test_invalid_or_existing_branch_changes_nothing'])
check('g2-discovery-ignores-record', f, ') in owned:', ') in ():', [t+'::test_custom_branch_lifecycle[asyncio-listed]'])
check('g2-delete-kept-branch', f, 'if not keep_branch:', 'if True:', [t+'::test_custom_branch_lifecycle[asyncio-kept]'])
check('g2-detach-person', f, 'tree = Worktree(path=at_path.resolve(), branch=branch, repo=repo.resolve())', 'await _git(repo, "checkout", "--detach")\n    tree = Worktree(path=at_path.resolve(), branch=branch, repo=repo.resolve())', [t+'::test_custom_branch_lifecycle[asyncio-person]'])
check('g2-keep-discarded-branch', f, 'if not keep_branch:', 'if False:', [t+'::test_custom_branch_can_be_discarded'])
check('g2-own-by-branch-only', f, 'or (\n                str(path.resolve()),\n                short,\n            ) in owned', 'or any(short == json.loads(r.split(" ", 1)[1])["branch"] for r in records.splitlines())', [t+'::test_a_reused_custom_branch_is_not_owned'])

check('g2-recreated-ownership', f,
      'directory = Path(await _git(Path(value["path"]), "rev-parse", "--absolute-git-dir"))\n            if (directory / "shadow-hdk-owner").read_text(encoding="utf-8") != value["nonce"]:\n                continue',
      'None', [t+'::test_recreating_the_same_path_and_branch_is_a_different_worktree'])
