"""Anchored mutants, no bytecode caches, behavioural failures only, exact restoration."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path(__file__).parent
PYTHON = ROOT / '.venv/bin/python'
TEST = 'tests/adapters/recording/test_a_socket_offer_honours_modes.py'

def check(label: str, file: str, old: str, new: str, selection: list[str]) -> None:
    path = ROOT / file
    before = path.read_bytes()
    source = before.decode()
    if source.count(old) != 1:
        raise RuntimeError(f'{label}: ambiguous/missing anchor')
    for pyc in (path.parent/'__pycache__').glob(path.stem+'.*.pyc'):
        pyc.unlink()
    try:
        path.write_text(source.replace(old, new, 1))
        done = subprocess.run([str(PYTHON), '-B', '-m', 'pytest', '-q', '--timeout=45', *selection],
            cwd=ROOT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'}, capture_output=True, text=True, timeout=120)
        output = done.stdout + done.stderr
        (EVIDENCE / (label+'.txt')).write_text(output)
        if done.returncode == 0 or 'AssertionError' not in output and 'DID NOT RAISE' not in output:
            raise RuntimeError(f'{label}: survived or failed before behavioural assertion: {output[-1200:]}')
        print(label, 'BITES', output.strip().splitlines()[-1], flush=True)
    finally:
        path.write_bytes(before)
        for pyc in (path.parent/'__pycache__').glob(path.stem+'.*.pyc'):
            pyc.unlink()
    if path.read_bytes() != before:
        raise RuntimeError('source not restored')

if __name__ == '__main__':
    check('g1-no-forward', 'src/shadow_hdk/adapters/recording/offer.py',
          'self._holder.narrow_to(names)', 'self._holder.narrow_to(())', [TEST])
    done = subprocess.run([str(PYTHON), '-B', '-m', 'pytest', '-q', TEST], cwd=ROOT,
                          capture_output=True, text=True, check=True)
    print('restored control', done.stdout.strip(), flush=True)
