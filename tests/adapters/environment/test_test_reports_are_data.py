"""JUnit cases, not human console prose, determine counts and failing names."""

from shadow_hdk.adapters.workbench.reports import junit_results
from shadow_hdk.kernel import Completed, Refused


def test_nested_suites_count_cases_once_and_preserve_failures_skips_and_output() -> None:
    report = """<testsuites tests="4"><testsuite tests="4"><testsuite tests="4">
      <testcase classname="app.api" name="works"/>
      <testcase classname="app.api" name="fails"><failure message="wrong">assert 1 == 2</failure>
        <system-out>debug detail</system-out><system-err>stderr detail</system-err></testcase>
      <testcase classname="app.api" name="errors"><error type="RuntimeError">boom</error></testcase>
      <testcase classname="app.api" name="later"><skipped message="requires database"/></testcase>
      </testsuite><system-out>suite output</system-out></testsuite></testsuites>"""
    result = junit_results(report)
    assert isinstance(result, Completed), result
    assert isinstance(result.output, dict)
    assert {k: result.output[k] for k in ("total", "passed", "failed", "skipped")} == {
        "total": 4,
        "passed": 1,
        "failed": 2,
        "skipped": 1,
    }
    assert result.output["failing_names"] == ["app.api.fails", "app.api.errors"]
    assert all(
        word in str(result.output)
        for word in (
            "assert 1 == 2",
            "debug detail",
            "stderr detail",
            "boom",
            "requires database",
            "suite output",
        )
    )


def test_reports_do_not_expand_entities_or_claim_incomplete_or_malformed_results() -> None:
    for report in (
        '<!DOCTYPE testsuite [<!ENTITY secret SYSTEM "file:///etc/passwd">]><testsuite>&secret;</testsuite>',
        '<testsuite tests="2"><testcase name="only one"/></testsuite>',
        '<other><testcase name="unrelated XML"/></other>',
        "<testsuite>",
    ):
        result = junit_results(report)
        assert isinstance(result, Refused), result
        assert "test report" in result.reason
