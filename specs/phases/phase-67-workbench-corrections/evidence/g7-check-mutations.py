"""Workbench regressions must reach their behavioural assertions and restore exact source."""
import runpy

check = runpy.run_path('specs/phases/phase-67-workbench-corrections/evidence/check-mutations.py')['check']
e = 'src/shadow_hdk/runtime/environment.py'
h = 'src/shadow_hdk/adapters/workbench/host.py'
r = 'src/shadow_hdk/adapters/workbench/reports.py'
l = 'src/shadow_hdk/adapters/workbench/listeners.py'
c = 'src/shadow_hdk/adapters/workbench/components.py'
t = 'tests/adapters/environment/test_the_host_watches_jobs_without_consuming_agent_output.py'
p = 'tests/adapters/environment/test_test_reports_are_data.py'
watch = [t+'::test_host_and_agent_readers_share_a_job_but_never_consume_each_others_output']
page = [t+'::test_output_cursors_survive_truncation_and_paginate_without_silent_loss']
report = [p+'::test_nested_suites_count_cases_once_and_preserve_failures_skips_and_output']
negative = [p+'::test_reports_do_not_expand_entities_or_claim_incomplete_or_malformed_results']
checks = [
    ('g7-host-consumes-agent', e, 'return _completed(job.observe(cursor, limit))', 'result = job.observe(cursor, limit)\n        job.read_to = len(job.said)\n        return _completed(result)', watch),
    ('g7-offset-reset', e, 'self.start += cut', 'self.start = 0', page),
    ('g7-cursor-ignored', e, 'first = max(cursor, self.start)', 'first = self.start', page),
    ('g7-limit-ignored', e, 'first - self.start + limit]', 'len(self.said)]', page),
    ('g7-more-hidden', e, '"more": end < self.start + len(self.said),', '"more": False,', page),
    ('g7-truncation-hidden', e, '"truncated": cursor < self.start,', '"truncated": False,', page),
    ('g7-future-accepted', e, 'or not 0 <= cursor <= job.start + len(job.said)', 'or cursor < 0', page),
    ('g7-job-running-false', e, '"running": self.process.returncode is None,', '"running": False,', watch),
    ('g7-job-exit-zero', e, '"exit_code": self.process.returncode,', '"exit_code": 0,', watch),
    ('g7-utf8-per-chunk', e, 'append(decoder.decode(chunk))', 'append(chunk.decode("utf-8", "replace"))', [t+'::test_split_utf8_is_decoded_once_and_cursors_count_characters']),
    ('g7-child-survives', e, 'end_the_group(self.process)', 'None', [t+'::test_stopping_an_exited_leader_still_ends_its_owned_child']),
    ('g7-person-run-ignored', h, 'return await self.environment.invoke("run_shell", {"command": command})', 'return Completed({})', [t+'::test_the_person_runs_and_reads_in_the_same_copy_without_an_agent']),
    ('g7-listeners-empty', l, 'return tuple(found[key] for key in sorted(found))', 'return ()', [t+'::test_a_silent_server_has_a_verified_listener_instead_of_a_guessed_url']),
    ('g7-listeners-guessed', l, '"verified": True,', '"verified": False,', [t+'::test_a_silent_server_has_a_verified_listener_instead_of_a_guessed_url']),
    ('g7-report-case-double-count', r, '"total": len(cases),', '"total": len(cases) * 2,', report),
    ('g7-report-passed-lost', r, 'passed += 1', 'passed += 0', report),
    ('g7-report-skipped-lost', r, 'skipped += 1', 'skipped += 0', report),
    ('g7-report-failing-name-lost', r, 'failed.append(identity)', 'failed.append(name)', report),
    ('g7-report-failure-output-lost', r, '"output": "".join(f.itertext()),', '"output": "",', report),
    ('g7-report-case-stdout-lost', r, '"stdout": case.findtext("system-out", ""),', '"stdout": "",', report),
    ('g7-report-case-stderr-lost', r, '"stderr": case.findtext("system-err", ""),', '"stderr": "",', report),
    ('g7-report-skip-reason-lost', r, 'skip.attrib.get("message", "") if skip is not None else None', 'None', report),
    ('g7-report-incomplete-accepted', r, 'if int(suite.attrib["tests"]) != actual:', 'if False:', negative),
    ('g7-report-wrong-root-accepted', r, 'if root.tag not in ("testsuite", "testsuites"):', 'if False:', negative),
    ('g7-pack-report-no-read', c, 'return await self._door.results(str(inputs["path"]))', 'return Refused("missing")', [t+'::test_workbench_reads_are_governed_and_reports_use_the_same_confined_file_door']),
    ('g7-pack-ignores-fields', c, 'and inputs.keys() == {"path"}', '', [t+'::test_workbench_reads_are_governed_and_reports_use_the_same_confined_file_door']),
]
for arguments in checks:
    check(*arguments)
