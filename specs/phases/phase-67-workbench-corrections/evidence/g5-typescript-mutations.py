"""Build each mutated client before driving it over the actual Python wire."""
import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[4]
evidence = Path(__file__).parent
client = root / 'clients/typescript'
python = root / '.venv/bin/python'
test = 'tests/serve/test_a_typescript_host_serves_tools.py'


def check(label, file, old, new, selected):
    path = client / file
    before = path.read_bytes()
    assert before.decode().count(old) == 1
    try:
        path.write_text(before.decode().replace(old, new))
        subprocess.run(['npm', 'run', 'build'], cwd=client, check=True, capture_output=True)
        done = subprocess.run([str(python), '-B', '-m', 'pytest', '-q', selected], cwd=root,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'}, capture_output=True, text=True, timeout=120)
        output = done.stdout+done.stderr
        (evidence/(label+'.txt')).write_text(output)
        assert done.returncode != 0 and 'AssertionError' in output, output[-1400:]
        print(label, 'BITES', output.strip().splitlines()[-1], flush=True)
    finally:
        path.write_bytes(before)
        subprocess.run(['npm', 'run', 'build'], cwd=client, check=True, capture_output=True)
    assert path.read_bytes() == before


check('g5-ts-drops-scope', 'src/components.ts', '{ resource_scope: p.resource_scope }', '{ resource_scope: "missing" }', test+'::test_a_typescript_tool_is_called_back_over_http')
check('g5-ts-duplicate-owners', 'src/components.ts',
    'const callbacks = [...new Set([...owners, ...tools.map(t => t.releaseRun).filter((f): f is NonNullable<ToolOptions["releaseRun"]> => f !== undefined)])];',
    'const callbacks = [...owners, ...tools.map(t => t.releaseRun).filter((f): f is NonNullable<ToolOptions["releaseRun"]> => f !== undefined)];',
    test+'::test_typescript_cleanup_attempts_every_owner_and_reports_failures')
check('g5-ts-hides-cleanup-failure', 'src/components.ts', 'if (failures.length) throw', 'if (false) throw', test+'::test_typescript_cleanup_attempts_every_owner_and_reports_failures')
check('g5-ts-drops-raw-owner', 'src/client.ts', 'this.resourceOwners = options.onReleaseRun ? [options.onReleaseRun] : [];', 'this.resourceOwners = [];', test+'::test_typescript_cleanup_attempts_every_owner_and_reports_failures')
check('g5-ts-no-negotiation', 'src/client.ts', 'run_resources: true', 'run_resources: false', test+'::test_a_typescript_tool_is_called_back_over_http')
