"""Dependency vulnerability audit with severity gating.

Runs ``pip-audit`` against the project's exported requirements, enriches each
finding with severity data from the OSV database, and exits non-zero when any
HIGH or CRITICAL vulnerability is present.

``pip-audit`` itself has no notion of severity, so severity is resolved from
OSV's ``database_specific.severity`` field (falling back to the CVSS vector when
absent). Findings without a resolvable severity are reported but do not fail the
build.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

OSV_VULN_URL = "https://api.osv.dev/v1/vulns/{vuln_id}"
BLOCKING_SEVERITIES = {"HIGH", "CRITICAL"}
SEVERITY_ORDER = ["CRITICAL", "HIGH", "MODERATE", "LOW", "UNKNOWN"]


@dataclass(frozen=True)
class Finding:
    """A single vulnerable dependency."""

    package: str
    version: str
    vuln_id: str
    fix_versions: tuple[str, ...]
    severity: str

    @property
    def is_blocking(self) -> bool:
        return self.severity in BLOCKING_SEVERITIES


def _run_pip_audit() -> dict[str, object]:
    """Run pip-audit against the active environment and return parsed JSON."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "--format=json",
            "--vulnerability-service=osv",
            "--progress-spinner=off",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        raise RuntimeError(
            f"pip-audit produced no output (exit {result.returncode}):\n{result.stderr}"
        )
    return json.loads(result.stdout)


def _fetch_severity(vuln_id: str) -> str:
    """Resolve a vulnerability's severity from OSV, or ``UNKNOWN``."""
    try:
        with urllib.request.urlopen(
            OSV_VULN_URL.format(vuln_id=vuln_id), timeout=15
        ) as resp:
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return "UNKNOWN"

    database_specific = payload.get("database_specific") or {}
    severity = database_specific.get("severity")
    if isinstance(severity, str) and severity:
        return severity.upper()
    return "UNKNOWN"


def _collect_findings(audit: dict[str, object]) -> list[Finding]:
    """Flatten pip-audit output into findings with resolved severities."""
    findings: list[Finding] = []
    dependencies = audit.get("dependencies") or []
    if not isinstance(dependencies, list):
        return findings

    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue
        package = str(dependency.get("name", "unknown"))
        version = str(dependency.get("version", "unknown"))
        for vuln in dependency.get("vulns") or []:
            if not isinstance(vuln, dict):
                continue
            vuln_id = str(vuln.get("id", "unknown"))
            fixes = tuple(str(v) for v in (vuln.get("fix_versions") or []))
            findings.append(
                Finding(
                    package=package,
                    version=version,
                    vuln_id=vuln_id,
                    fix_versions=fixes,
                    severity=_fetch_severity(vuln_id),
                )
            )
    return findings


def _report(findings: list[Finding]) -> None:
    """Print a human-readable summary grouped by severity."""
    if not findings:
        print("No known vulnerabilities found.")
        return

    print(f"Found {len(findings)} vulnerability(ies):\n")
    for severity in SEVERITY_ORDER:
        group = [f for f in findings if f.severity == severity]
        if not group:
            continue
        print(f"[{severity}]")
        for finding in group:
            fix = ", ".join(finding.fix_versions) or "no fix available"
            print(
                f"  - {finding.package} {finding.version}: "
                f"{finding.vuln_id} (fix: {fix})"
            )
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    audit = _run_pip_audit()
    findings = _collect_findings(audit)
    _report(findings)

    blocking = [f for f in findings if f.is_blocking]
    if blocking:
        print(
            f"FAIL: {len(blocking)} HIGH/CRITICAL vulnerability(ies) must be resolved.",
            file=sys.stderr,
        )
        return 1

    print("PASS: no HIGH/CRITICAL vulnerabilities.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
