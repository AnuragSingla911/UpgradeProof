"""Adversarial transitions that do not need a package install.

These checks are part of the benchmark. They use a scripted session so a
deliberately bad proposal can be judged without pretending it is a model.
"""

from __future__ import annotations

from dataclasses import dataclass

from upgradeproof.harness import Budget, investigate, prepare_case
from upgradeproof.model import Proposal, Replacement, RunLog
from upgradeproof.proposers import FixedProposer
from upgradeproof.scripted import ScriptedSession


@dataclass
class TinyCase:
    id: str
    title: str
    package: str = "urllib3"
    from_version: str = "1.26.20"
    to_version: str = "2.2.3"


_BROKEN = "src/retryctx/client.py"
_BROKEN_TEXT = 'return Retry(total=3, method_whitelist=["GET", "HEAD"])\n'
_ERROR = (
    "src/retryctx/client.py:4: in build_retry\n"
    "E   TypeError: Retry.__init__() got an unexpected keyword argument 'method_whitelist'\n"
)


def run_guard_checks() -> list[dict[str, object]]:
    checks = [
        _invalid_baseline,
        _constraint_conflict,
        _verified_bump,
        _reject_test_edit,
        _reject_unrelated_edit,
        _reject_deleted_assert,
        _invented_api_fails_execution,
        _oracle_failure_is_not_success,
        _repeated_timeouts_stop,
        _abstain_is_unresolved,
    ]
    results = []
    for check in checks:
        results.append(check())
    return results


def _run(session: ScriptedSession, proposer, *, mode: str = "guard") -> object:
    prepared = prepare_case(TinyCase("guard", mode), session, Budget())
    return investigate(prepared, proposer, mode=mode, budget=Budget())


def _record(name: str, evidence, expected_verdict: str, expected_reason: str) -> dict[str, object]:
    ok = evidence.verdict == expected_verdict and expected_reason in evidence.reason
    return {
        "name": name,
        "ok": ok,
        "verdict": evidence.verdict,
        "reason": evidence.reason,
        "model_calls": evidence.model_calls,
        "delivered_patch": bool(evidence.patch),
    }


def _invalid_baseline() -> dict[str, object]:
    session = ScriptedSession(
        files={_BROKEN: _BROKEN_TEXT},
        public=[RunLog(False, "E   AssertionError: baseline\n")],
        upgrade=[RunLog(True, "should not run")],
    )
    evidence = _run(session, _noop())
    result = _record("invalid_baseline", evidence, "invalid_baseline", "original dependency")
    result["ok"] = bool(result["ok"]) and "upgrade" not in session.events
    return result


def _constraint_conflict() -> dict[str, object]:
    session = ScriptedSession(
        files={_BROKEN: _BROKEN_TEXT},
        public=[RunLog(True, "1 passed")],
        upgrade=[RunLog(False, "ERROR: ResolutionImpossible\nThe conflict is caused by:\n")],
    )
    evidence = _run(session, _noop())
    return _record("constraint_conflict", evidence, "constraint_conflict", "resolver")


def _verified_bump() -> dict[str, object]:
    session = ScriptedSession(
        files={"src/app.py": "x = 1\n", "requirements.txt": "urllib3==1.26.20\n"},
        public=[RunLog(True, "1 passed"), RunLog(True, "1 passed")],
        upgrade=[RunLog(True, "installed")],
        oracle=[RunLog(True, "1 passed")],
    )
    evidence = _run(session, _noop())
    result = _record("verified_bump", evidence, "verified_bump", "no source change")
    result["ok"] = bool(result["ok"]) and evidence.model_calls == 0
    return result


def _reject_test_edit() -> dict[str, object]:
    session = _failing_session()
    proposal = Proposal(
        source="model:scripted",
        replacements=(Replacement("tests/test_client.py", "assert True", "assert True or True"),),
        counts_as_model_call=True,
        trusted=False,
    )
    evidence = _run(session, FixedProposer(proposal))
    result = _record("reject_protected_test_edit", evidence, "unresolved", "protected test")
    result["ok"] = bool(result["ok"]) and evidence.patch == ""
    return result


def _reject_unrelated_edit() -> dict[str, object]:
    session = _failing_session(extra={"src/notes.py": "note = 1\n"})
    proposal = Proposal(
        source="model:scripted",
        replacements=(Replacement("src/notes.py", "note = 1", "note = 2"),),
        counts_as_model_call=True,
    )
    evidence = _run(session, FixedProposer(proposal))
    return _record("reject_unrelated_edit", evidence, "unresolved", "outside failure scope")


def _reject_deleted_assert() -> dict[str, object]:
    text = "def build_retry():\n    assert True\n    return Retry(method_whitelist=None)\n"
    session = _failing_session(files={_BROKEN: text})
    proposal = Proposal(
        source="model:scripted",
        replacements=(Replacement(_BROKEN, "    assert True\n    return Retry(method_whitelist=None)\n", "    return Retry(allowed_methods=None)\n"),),
        trusted=True,
    )
    evidence = _run(session, FixedProposer(proposal))
    return _record("reject_deleted_assert", evidence, "unresolved", "protected assertion")


def _invented_api_fails_execution() -> dict[str, object]:
    session = _failing_session(
        later_public=[
            RunLog(False, "E   TypeError: unexpected keyword argument 'allowed_methodz'\n"),
            RunLog(False, "E   TypeError: unexpected keyword argument 'allowed_methodz'\n"),
        ]
    )
    proposal = Proposal(
        source="model:scripted",
        replacements=(Replacement(_BROKEN, "method_whitelist=", "allowed_methodz="),),
        counts_as_model_call=True,
        trusted=True,
        rationale="invented api",
    )
    evidence = _run(session, FixedProposer(proposal))
    result = _record("invented_api_caught_by_execution", evidence, "unresolved", "tests_still_failing")
    result["ok"] = bool(result["ok"]) and evidence.patch == "" and "oracle" not in session.events
    return result


def _oracle_failure_is_not_success() -> dict[str, object]:
    session = _failing_session(
        later_public=[RunLog(True, "1 passed"), RunLog(True, "1 passed")],
        oracle=[RunLog(False, "E   AssertionError: hidden\n"), RunLog(False, "E   AssertionError: hidden\n")],
    )
    proposal = Proposal(
        source="model:scripted",
        replacements=(Replacement(_BROKEN, "method_whitelist=", "allowed_methods="),),
        counts_as_model_call=True,
        trusted=True,
    )
    evidence = _run(session, FixedProposer(proposal))
    result = _record("oracle_failure_not_delivered", evidence, "unresolved", "oracle_failed")
    result["ok"] = bool(result["ok"]) and evidence.verified is False and evidence.patch == ""
    return result


def _repeated_timeouts_stop() -> dict[str, object]:
    timeout = RunLog(False, "TIMEOUT", timed_out=True)
    session = _failing_session(later_public=[timeout, timeout])
    proposal = Proposal(
        source="model:scripted",
        replacements=(Replacement(_BROKEN, "method_whitelist=", "allowed_methods="),),
        trusted=True,
    )
    evidence = _run(session, FixedProposer(proposal))
    return _record("retry_limit", evidence, "unresolved", "retry_limit")


def _abstain_is_unresolved() -> dict[str, object]:
    session = _failing_session()
    evidence = _run(session, FixedProposer(Proposal.abstention("rule", "no promoted repair matches this failure")))
    result = _record("abstain", evidence, "unresolved", "no promoted repair")
    result["ok"] = bool(result["ok"]) and evidence.model_calls == 0
    return result


def _failing_session(
    *,
    files: dict[str, str] | None = None,
    extra: dict[str, str] | None = None,
    later_public: list[RunLog] | None = None,
    oracle: list[RunLog] | None = None,
) -> ScriptedSession:
    body = dict(files or {_BROKEN: _BROKEN_TEXT})
    if extra:
        body.update(extra)
    public = [RunLog(True, "1 passed"), RunLog(False, _ERROR)]
    public.extend(later_public or [])
    return ScriptedSession(files=body, public=public, upgrade=[RunLog(True, "installed")], oracle=oracle)


def _noop() -> FixedProposer:
    return FixedProposer(Proposal.abstention("guard", "unused"))
