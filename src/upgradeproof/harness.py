"""State machine for one dependency-upgrade investigation.

The transitions are the product. A proposer never decides that a run
succeeded: only public tests and the hidden oracle can do that, and the
oracle output is not fed back into the proposer.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from upgradeproof import LIMITATION
from upgradeproof.checks import classify_failure, suspect_source_files, validate_replacements
from upgradeproof.model import Evidence, Proposal, ProposalRequest, RunLog

_VERIFIED = {"verified_repair", "verified_bump"}


@dataclass
class Budget:
    max_repair_attempts: int = 2
    max_model_calls: int = 2
    max_tool_failures: int = 2
    case_timeout_seconds: float = 180


@dataclass
class PreparedCase:
    """Environment after baseline and the dependency change, shared by modes."""

    title: str
    case_id: str
    package: str
    from_version: str
    to_version: str
    session: object
    baseline: RunLog
    upgrade: RunLog | None
    upgraded_tests: RunLog | None
    failure_class: str | None
    setup_seconds: float
    setup_error: str | None = None


def prepare_case(case, session, budget: Budget | None = None) -> PreparedCase:
    """Install the original pin, test it, then install the requested pin."""

    budget = budget or Budget()
    started = time.perf_counter()
    setup = session.setup()
    if setup.timed_out or not setup.ok:
        return PreparedCase(
            title=case.title,
            case_id=case.id,
            package=case.package,
            from_version=case.from_version,
            to_version=case.to_version,
            session=session,
            baseline=RunLog(False, ""),
            upgrade=None,
            upgraded_tests=None,
            failure_class=None,
            setup_seconds=time.perf_counter() - started,
            setup_error=setup.tail() or "environment setup failed",
        )
    baseline = session.run_public_tests()
    upgrade = None
    upgraded_tests = None
    failure_class = None
    if baseline.ok and not baseline.timed_out:
        upgrade = _with_timeout_retry(session.upgrade_dependency, budget)
        if upgrade.ok and not upgrade.timed_out:
            session.base_files = session.snapshot()
            upgraded_tests = session.run_public_tests()
            if not upgraded_tests.ok:
                failure_class = classify_failure(upgraded_tests.output)
    return PreparedCase(
        title=case.title,
        case_id=case.id,
        package=case.package,
        from_version=case.from_version,
        to_version=case.to_version,
        session=session,
        baseline=baseline,
        upgrade=upgrade,
        upgraded_tests=upgraded_tests,
        failure_class=failure_class,
        setup_seconds=time.perf_counter() - started,
    )


def investigate(prepared: PreparedCase, proposer, *, mode: str, budget: Budget | None = None, expected: str | None = None) -> Evidence:
    budget = budget or Budget()
    started = time.perf_counter()
    timeline: list[dict[str, object]] = []
    model_calls = 0
    rejections: list[str] = []

    def finish(verdict: str, reason: str, **kwargs) -> Evidence:
        evidence = Evidence(
            case_id=prepared.case_id,
            title=prepared.title,
            mode=mode,
            verdict=verdict,
            reason=reason,
            model_calls=model_calls,
            wall_clock_seconds=round(prepared.setup_seconds + (time.perf_counter() - started), 3),
            setup_seconds=round(prepared.setup_seconds, 3),
            estimated_cost_usd=_cost(mode, model_calls),
            rejections=rejections,
            timeline=timeline,
            limitation=LIMITATION,
            expected_verdict=expected,
            **kwargs,
        )
        evidence.expectation_met = expected is None or evidence.verdict == expected
        if verdict not in _VERIFIED:
            evidence.patch = ""
            if prepared.upgrade is not None and prepared.upgrade.ok:
                prepared.session.restore_base()
        return evidence

    if prepared.setup_error:
        timeline.append({"state": "setup", "ok": False})
        return finish("unresolved", "environment_setup_failed: " + prepared.setup_error)

    baseline = prepared.baseline
    timeline.append({"state": "baseline", "ok": baseline.ok, "timed_out": baseline.timed_out, "output": baseline.tail(700)})
    if baseline.timed_out:
        return finish("unresolved", "command_timeout", baseline_passed=False, failure_class="timeout")
    if not baseline.ok:
        return finish(
            "invalid_baseline",
            "public tests failed on the original dependency",
            baseline_passed=False,
            failure_class=classify_failure(baseline.output),
        )

    upgrade = prepared.upgrade
    assert upgrade is not None
    timeline.append({"state": "upgrade", "ok": upgrade.ok, "timed_out": upgrade.timed_out, "output": upgrade.tail(700)})
    if upgrade.ok:
        # Modes and probes share one installed environment. Always start from
        # the upgraded, unpatched sources captured during preparation.
        prepared.session.restore_base()
    if upgrade.timed_out:
        return finish("unresolved", "retry_limit", baseline_passed=True, upgrade_passed=False, failure_class="timeout")
    if not upgrade.ok:
        failure_class = classify_failure(upgrade.output)
        verdict = "constraint_conflict" if failure_class == "constraint_conflict" else "unresolved"
        reason = "dependency resolver rejected the requested version" if verdict == "constraint_conflict" else "upgrade_install_failed"
        return finish(verdict, reason, baseline_passed=True, upgrade_passed=False, failure_class=failure_class)

    retest = prepared.upgraded_tests
    assert retest is not None
    timeline.append(
        {
            "state": "retest",
            "ok": retest.ok,
            "failure_class": prepared.failure_class,
            "output": retest.tail(700),
        }
    )
    if retest.timed_out:
        return finish("unresolved", "retry_limit", baseline_passed=True, upgrade_passed=True, failure_class="timeout")
    if retest.ok:
        return _accept_bump(prepared, finish, timeline)

    feedback = ""
    attempts = 0
    tool_failures = 0
    last_reason = "no_repair"
    failure_class = prepared.failure_class or "unknown"
    while attempts < budget.max_repair_attempts:
        if time.perf_counter() - started > budget.case_timeout_seconds:
            return finish(
                "unresolved",
                "case_timeout",
                attempts=attempts,
                failure_class=failure_class,
                baseline_passed=True,
                upgrade_passed=True,
                public_tests_passed=False,
            )
        attempts += 1
        prepared.session.restore_base()
        files = prepared.session.application_files()
        request = ProposalRequest(
            case_id=prepared.case_id,
            package=prepared.package,
            from_version=prepared.from_version,
            to_version=prepared.to_version,
            failure_class=failure_class,
            log=_truncate(retest.output, 4000),
            files=files,
            feedback=feedback,
            attempt=attempts,
        )
        proposal = proposer.propose(request)
        if proposal.counts_as_model_call:
            model_calls += 1
        timeline.append(
            {
                "state": "propose",
                "attempt": attempts,
                "source": proposal.source,
                "abstain": proposal.abstain,
                "model_call": proposal.counts_as_model_call,
            }
        )
        if model_calls > budget.max_model_calls:
            return finish(
                "unresolved",
                "model_budget",
                attempts=attempts,
                failure_class=failure_class,
                repair_source=proposal.source,
                baseline_passed=True,
                upgrade_passed=True,
            )
        if proposal.abstain:
            return finish(
                "unresolved",
                proposal.abstain_reason or "abstained",
                attempts=attempts,
                failure_class=failure_class,
                repair_source=proposal.source,
                baseline_passed=True,
                upgrade_passed=True,
                public_tests_passed=False,
            )
        suspects = suspect_source_files(retest.output, files)
        reasons = validate_replacements(
            files,
            list(proposal.replacements),
            trusted=proposal.trusted,
            suspects=suspects,
        )
        if reasons:
            rejections.extend(reasons)
            last_reason = "patch_rejected: " + "; ".join(reasons)
            timeline.append({"state": "reject_patch", "attempt": attempts, "reasons": reasons})
            feedback = last_reason
            continue
        prepared.session.restore_base()
        applied = prepared.session.apply(proposal.replacements)
        timeline.append({"state": "apply", "attempt": attempts, "ok": applied.ok})
        if not applied.ok:
            last_reason = "apply_failed"
            feedback = applied.tail()
            continue
        checked = prepared.session.run_public_tests()
        if checked.timed_out:
            tool_failures += 1
            timeline.append({"state": "retest_repair", "attempt": attempts, "timed_out": True})
            if tool_failures >= budget.max_tool_failures:
                return finish(
                    "unresolved",
                    "retry_limit",
                    attempts=attempts,
                    failure_class="timeout",
                    repair_source=proposal.source,
                    baseline_passed=True,
                    upgrade_passed=True,
                )
            last_reason = "retry_limit"
            feedback = "The test command timed out."
            continue
        if not checked.ok:
            last_reason = "tests_still_failing"
            failure_class = classify_failure(checked.output)
            feedback = _truncate(checked.output, 2500)
            timeline.append({"state": "retest_repair", "attempt": attempts, "ok": False, "failure_class": failure_class})
            continue
        oracle = prepared.session.run_oracle()
        timeline.append({"state": "oracle", "attempt": attempts, "ok": oracle.ok})
        if oracle.timed_out:
            tool_failures += 1
            if tool_failures >= budget.max_tool_failures:
                return finish("unresolved", "retry_limit", attempts=attempts, failure_class="timeout", repair_source=proposal.source, baseline_passed=True, upgrade_passed=True, public_tests_passed=True)
            continue
        if not oracle.ok:
            last_reason = "oracle_failed"
            # The proposer is told that hidden checks failed, not what they assert.
            feedback = (
                "Hidden evaluation checks failed after the public tests passed. "
                "Do not modify tests. Propose a smaller behavior-preserving repair or abstain."
            )
            continue
        no_oracle = oracle.output.startswith("no hidden oracle")
        return finish(
            "verified_repair",
            "public tests passed" if no_oracle else "public tests and hidden evaluation checks passed",
            attempts=attempts,
            failure_class=prepared.failure_class,
            repair_source=proposal.source,
            patch=prepared.session.diff(),
            baseline_passed=True,
            upgrade_passed=True,
            public_tests_passed=True,
            oracle_passed=None if no_oracle else True,
        )

    prepared.session.restore_base()
    public_ok = last_reason == "oracle_failed"
    return finish(
        "unresolved",
        last_reason,
        attempts=attempts,
        failure_class=failure_class,
        baseline_passed=True,
        upgrade_passed=True,
        public_tests_passed=public_ok,
        oracle_passed=False if public_ok else None,
    )


def _accept_bump(prepared: PreparedCase, finish, timeline) -> Evidence:
    oracle = prepared.session.run_oracle()
    timeline.append({"state": "oracle", "ok": oracle.ok, "bump": True})
    if oracle.timed_out:
        return finish("unresolved", "retry_limit", baseline_passed=True, upgrade_passed=True, public_tests_passed=True, failure_class="timeout")
    if not oracle.ok:
        return finish(
            "unresolved",
            "public tests passed after the version bump but hidden evaluation checks failed",
            baseline_passed=True,
            upgrade_passed=True,
            public_tests_passed=True,
            oracle_passed=False,
            failure_class=classify_failure(oracle.output),
        )
    no_oracle = oracle.output.startswith("no hidden oracle")
    return finish(
        "verified_bump",
        "the upgraded pin passed public tests with no source change"
        if no_oracle
        else "the upgraded dependency passed public tests and hidden evaluation checks with no source change",
        baseline_passed=True,
        upgrade_passed=True,
        public_tests_passed=True,
        oracle_passed=None if no_oracle else True,
        patch=prepared.session.diff(),
        repair_source="harness:version-bump",
    )


def _with_timeout_retry(operation, budget: Budget) -> RunLog:
    log = operation()
    if log.timed_out and budget.max_tool_failures > 1:
        log = operation()
    return log


def _cost(mode: str, model_calls: int) -> float:
    if mode != "hosted" or model_calls == 0:
        return 0.0
    raw = os.environ.get("UPGRADEPROOF_PRICE_PER_CALL", "")
    if not raw:
        return 0.0
    try:
        return round(model_calls * float(raw), 6)
    except ValueError:
        return 0.0


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]
