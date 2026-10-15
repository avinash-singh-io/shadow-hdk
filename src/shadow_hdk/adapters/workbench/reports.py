"""Bounded, entity-free JUnit reports. Console text is never interpreted as a test result."""

from pydantic import JsonValue

from shadow_hdk.kernel import Completed, Observation, Refused


def junit_results(report: JsonValue) -> Observation:
    if not isinstance(report, str) or len(report.encode()) > 8_000_000:
        return Refused("test report must be XML text of at most 8 MB")
    try:
        from defusedxml.ElementTree import fromstring

        root = fromstring(report, forbid_dtd=True, forbid_entities=True, forbid_external=True)
        if root.tag not in ("testsuite", "testsuites"):
            raise ValueError("expected testsuite or testsuites")
        for suite in root.iter():
            if suite.tag in ("testsuite", "testsuites") and "tests" in suite.attrib:
                actual = sum(1 for _ in suite.iter("testcase"))
                if int(suite.attrib["tests"]) != actual:
                    raise ValueError("declared test count differs from testcase count")
        cases: list[JsonValue] = []
        failed: list[JsonValue] = []
        passed, skipped = 0, 0
        for case in root.iter("testcase"):
            name = case.attrib.get("name", "")
            if not name:
                raise ValueError("testcase must have a name")
            classname = case.attrib.get("classname", "")
            identity = f"{classname}.{name}" if classname else name
            failures = [child for child in case if child.tag in ("failure", "error")]
            skip = case.find("skipped")
            if failures and skip is not None:
                raise ValueError("testcase cannot be both skipped and failed")
            status = "failed" if failures else "skipped" if skip is not None else "passed"
            if status == "failed":
                failed.append(identity)
            elif status == "skipped":
                skipped += 1
            else:
                passed += 1
            cases.append(
                {
                    "name": identity,
                    "status": status,
                    "failures": [
                        {
                            "kind": f.tag,
                            "message": f.attrib.get("message", ""),
                            "type": f.attrib.get("type", ""),
                            "output": "".join(f.itertext()),
                        }
                        for f in failures
                    ],
                    "skip_reason": skip.attrib.get("message", "") if skip is not None else None,
                    "stdout": case.findtext("system-out", ""),
                    "stderr": case.findtext("system-err", ""),
                }
            )
        return Completed(
            {
                "format": "junit",
                "total": len(cases),
                "passed": passed,
                "failed": len(failed),
                "skipped": skipped,
                "failing_names": failed,
                "cases": cases,
                "stdout": [
                    item.text or ""
                    for suite in root.iter()
                    if suite.tag in ("testsuite", "testsuites")
                    for item in suite.findall("system-out")
                ],
                "stderr": [
                    item.text or ""
                    for suite in root.iter()
                    if suite.tag in ("testsuite", "testsuites")
                    for item in suite.findall("system-err")
                ],
            }
        )
    except ImportError:
        return Refused("test report parser requires shadow-hdk[workbench]")
    except Exception as error:
        return Refused(f"invalid test report: {type(error).__name__}: {error}")
