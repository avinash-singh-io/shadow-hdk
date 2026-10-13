from pathlib import Path
import hashlib
import subprocess

ROOT = Path('/Users/avinash/Workspace/Projects/shadow-workspace/shadow-hdk')
OUT = ROOT / 'specs/phases/phase-67-workbench-corrections/evidence'
runtime_test = 'tests/runtime/test_run_resources.py'
wire_test = 'tests/wire/test_images_and_resources.py'
turn_test = 'tests/runtime/test_conversation_resources_survive_approval.py'

def replace(old, new, count=1):
    def change(text):
        assert text.count(old) >= count, old
        return text.replace(old, new, count)
    return change

def last(old, new):
    def change(text):
        a, sep, b = text.rpartition(old)
        assert sep, old
        return a + new + b
    return change

cases = [
 ('release-at-park', 'runtime/loop.py', replace(' and not parked', '', 2), runtime_test+'::test_a_park_keeps_the_resource_until_the_resumed_run_ends'),
 ('runtime-owns-host-scope', 'runtime/bindings.py', replace('resource_owner is None and resource_scope is None', 'resource_owner is None'), runtime_test+'::test_a_thread_owns_one_scope_across_turns_and_closes_it_once'),
 ('turn-scope-omitted', 'runtime/conversation.py', replace('                resource_scope=self.id,\n', ''), runtime_test+'::test_a_thread_owns_one_scope_across_turns_and_closes_it_once'),
 ('settle-scope-omitted', 'runtime/conversation.py', replace('            resource_scope=self.id,\n', ''), turn_test),
 ('close-scope-omitted', 'runtime/conversation.py', replace('failure = await release_resources(self._ports.components, self.id)', 'failure = None'), runtime_test+'::test_a_thread_owns_one_scope_across_turns_and_closes_it_once'),
 ('conversation-close-not-shielded', 'runtime/conversation.py', replace('_, cancelled = await settle_resources(self._closing_resources)', 'await self._closing_resources\n        cancelled = False'), runtime_test+'::test_conversation_close_settles_teardown_before_delivering_cancellation'),
 ('thread-close-not-shielded', 'runtime/threads.py', replace('_, cancelled = await settle_resources(self._closing)', 'await self._closing\n        cancelled = False'), runtime_test+'::test_repeated_cancellation_waits_for_the_thread_hold_to_release'),
 ('thread-hold-not-released-on-failure', 'runtime/threads.py', replace('''        try:
            await self.conversation.close()
        finally:
            try:
                await self._remember_session()
            finally:
                await self._let_go_of_hold()''', '''        await self.conversation.close()
        await self._remember_session()
        await self._let_go_of_hold()'''), runtime_test+'::test_a_thread_cleanup_failure_releases_the_hold_and_tries_every_port'),
 ('teardown-not-deduplicated', 'runtime/resources.py', replace('resources = {id(port): port for port in ports if isinstance(port, RunResourcePort)}', 'resources = {i: port for i, port in enumerate(ports) if isinstance(port, RunResourcePort)}'), runtime_test+'::test_a_thread_owns_one_scope_across_turns_and_closes_it_once'),
 ('teardown-stops-at-first-error', 'runtime/resources.py', replace('failures.append(f"{type(error).__name__}: {error}")', 'return f"{type(error).__name__}: {error}"'), runtime_test+'::test_a_thread_cleanup_failure_releases_the_hold_and_tries_every_port'),
 ('wire-driver-scope-omitted', 'wire/sides.py', replace('            resource_scope=params.get("resource_scope"),\n', ''), wire_test+'::test_a_wire_host_owns_one_scope_across_runs_and_releases_aliases_once'),
 ('wire-run-scope-omitted', 'wire/sides.py', replace('                "resource_scope": options.resource_scope,\n', ''), wire_test+'::test_a_wire_host_owns_one_scope_across_runs_and_releases_aliases_once'),
 ('wire-resume-scope-omitted', 'wire/sides.py', last('                "resource_scope": options.resource_scope,\n', ''), wire_test+'::test_a_wire_resume_keeps_the_hosts_resource_scope'),
]
for name, relative, change, target in cases:
    source = ROOT / 'src/shadow_hdk' / relative
    before = source.read_bytes()
    try:
        source.write_text(change(before.decode()))
        for cache in source.parent.glob('__pycache__/'+source.stem+'.*.pyc'):
            cache.unlink()
        result = subprocess.run(['uv','run','pytest','-q',target],cwd=ROOT,capture_output=True,text=True,timeout=25)
        (OUT/('g5-lifetime-mutant-'+name+'.txt')).write_text(result.stdout+result.stderr)
        if result.returncode != 1 or 'FAILED ' not in result.stdout or 'ERROR collecting' in result.stdout:
            raise RuntimeError(f'{name} did not reach a failing behavioral control: {result.returncode}\n{result.stdout}')
        print(name+': BITES', flush=True)
    finally:
        source.write_bytes(before)
        for cache in source.parent.glob('__pycache__/'+source.stem+'.*.pyc'):
            cache.unlink()
        assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(before).digest()
control = subprocess.run(['uv','run','pytest','-q',runtime_test,turn_test,wire_test],cwd=ROOT,capture_output=True,text=True,timeout=30)
(OUT/'g5-lifetime-restored-control.txt').write_text(control.stdout+control.stderr)
assert control.returncode == 0, control.stdout
print(control.stdout)
