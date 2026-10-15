"""Acceptance smoke on a pinned upstream CPython checkout, separate from frozen CI budgets."""
import asyncio
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.adapters.environment.history import GitHistory
from shadow_hdk.kernel import Completed


async def check(root: Path) -> dict:
    def git(*args):
        return subprocess.check_output(['git', '--no-optional-locks', *args], cwd=root).strip().decode()
    head = git('rev-parse', 'HEAD')
    index = Path(git('rev-parse', '--git-path', 'index'))
    if not index.is_absolute():
        index = root / index
    index_before = hashlib.sha256(index.read_bytes()).hexdigest()
    original_status = git('status', '--porcelain')
    assert not original_status
    target = root / 'README.rst'
    original = target.read_bytes()
    timings = {}
    history = GitHistory(root)
    env = await LocalEnvironment.open(root, mode='full')
    async def measured(name, operation):
        start = time.perf_counter()
        answer = await operation
        timings[name] = round(time.perf_counter()-start, 4)
        return answer
    try:
        found = await measured('glob', env.invoke('glob', {'pattern':'**/README.rst'}))
        assert isinstance(found, Completed) and 'README.rst' in str(found.output)
        matched = await measured('grep', env.invoke('grep', {'pattern':'Python', 'glob':'**/README.rst'}))
        assert isinstance(matched, Completed) and 'README.rst' in str(matched.output)
        snapshot = await measured('snapshot_cold', history.snapshot('upstream source'))
        await measured('snapshot_unchanged', history.snapshot('unchanged'))
        target.write_bytes(original+b'\nexternal shell edit\n')
        await measured('snapshot_one_edit', history.snapshot('external edit'))
        await measured('restore', history.restore(snapshot))
        assert target.read_bytes() == original
        assert git('rev-parse','HEAD') == head and git('status','--porcelain') == original_status
        assert hashlib.sha256(index.read_bytes()).hexdigest() == index_before
    finally:
        target.write_bytes(original)
        await env.close()
    return {'repository':'https://github.com/python/cpython', 'tag':'v3.14.0', 'commit':head,
            'tracked_files':len(git('ls-files').splitlines()), 'platform':platform.platform(),
            'python':platform.python_version(), 'seconds':timings,
            'restored':True, 'head_and_user_index_unchanged':True}


if __name__ == '__main__':
    print(json.dumps(asyncio.run(check(Path('/tmp/hdk67-cpython-3.14.0'))), indent=2))
