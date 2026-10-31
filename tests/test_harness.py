"""Unit tests for the gates. Package installs live in the benchmark command."""

from pathlib import Path

import pytest

from upgradeproof.checks import (
    classify_failure,
    resolve_inside,
    rewrite_equality_pin,
    validate_diff_text,
    validate_replacements,
)
from upgradeproof.guards import run_guard_checks
from upgradeproof.knowledge import (
    PromoteError,
    extract_skill_fence,
    load_rules,
    load_skill_rules,
    promote_skill,
)
from upgradeproof.mcp_server import handle
from upgradeproof.model import ProposalRequest, Replacement
from upgradeproof.proposers import CpuProposer, HostedProposer

ROOT = Path(__file__).resolve().parents[1]


def test_guard_checks_hold():
    results = run_guard_checks()
    failed = [item for item in results if not item["ok"]]
    assert failed == []
    assert {item["name"] for item in results} >= {
        "invalid_baseline",
        "constraint_conflict",
        "verified_bump",
        "reject_protected_test_edit",
        "reject_unrelated_edit",
        "reject_deleted_assert",
        "invented_api_caught_by_execution",
        "oracle_failure_not_delivered",
        "retry_limit",
        "abstain",
    }


def test_failure_classes():
    assert classify_failure("E   TypeError: f() got an unexpected keyword argument 'method_whitelist'") == "unexpected_keyword"
    assert classify_failure("E   ImportError: cannot import name 'url_quote'") == "import_error"
    assert classify_failure("E   KeyError: 'upgradeproof.plugins'") == "key_error"
    assert classify_failure("ERROR: ResolutionImpossible\nThe conflict is caused by:\n") == "constraint_conflict"


def test_pin_rewrite_is_exact():
    text = "urllib3==1.26.20\npytest==8.3.5\n"
    assert rewrite_equality_pin(text, "urllib3", "2.2.3") == "urllib3==2.2.3\npytest==8.3.5\n"
    assert rewrite_equality_pin("urllib3==1.26.20\n", "urllib3", "2.2.3") == "urllib3==2.2.3\n"
    with pytest.raises(ValueError):
        rewrite_equality_pin(text, "missing", "1")


def test_diff_text_rejects_tests_and_asserts():
    diff = "--- a/tests/test_app.py\n+++ b/tests/test_app.py\n@@\n-    assert value() == 1\n+    assert True\n"
    reasons = validate_diff_text(diff)
    assert any("protected test" in reason for reason in reasons)
    assert any("assertion" in reason for reason in reasons)
    assert validate_diff_text("--- a/src/app.py\n+++ b/src/app.py\n@@\n-x = 1\n+x = 2\n") == []


def test_promoted_rules_match_skill_fences():
    rules = {rule.id: rule for rule in load_rules(ROOT / "rules" / "promoted")}
    skills = {rule.id: rule for rule in load_skill_rules(ROOT / "skills")}
    assert set(rules) == set(skills) == {
        "urllib3-retry-method-whitelist",
        "werkzeug-url-quote",
        "importlib-entry-points",
        "itsdangerous-timed-serializer",
        "packaging-legacy-version",
    }
    for name, rule in rules.items():
        skill = skills[name]
        assert rule.package == skill.package
        assert rule.error_class == skill.error_class
        assert rule.error_contains == skill.error_contains
        assert rule.replacements == skill.replacements


def test_prose_skill_is_not_executable():
    text = (ROOT / "skills" / "markupsafe" / "SKILL.md").read_text(encoding="utf-8")
    assert "soft_str" in text
    assert extract_skill_fence(text) is None
    assert all(rule.package != "markupsafe" for rule in load_skill_rules(ROOT / "skills"))


def test_promote_requires_acceptance_and_a_verified_verdict(tmp_path: Path):
    skill = (ROOT / "skills" / "urllib3" / "SKILL.md").read_text(encoding="utf-8")
    with pytest.raises(PromoteError):
        promote_skill(skill, tmp_path, accept=False, evidence_verdict="verified_repair")
    with pytest.raises(PromoteError):
        promote_skill(skill, tmp_path, accept=True, evidence_verdict="unresolved")
    target = promote_skill(skill, tmp_path, accept=True, evidence_verdict="verified_repair")
    assert target.is_file()
    loaded = load_rules(tmp_path)
    assert loaded[0].id == "urllib3-retry-method-whitelist"


def test_hosted_mode_does_not_call_the_network_when_unconfigured():
    def explode(*_args, **_kwargs):
        raise AssertionError("hosted mode tried to use the network")

    proposer = HostedProposer(environ={}, opener=explode)
    proposal = proposer.propose(
        ProposalRequest(
            case_id="x",
            package="urllib3",
            from_version="1",
            to_version="2",
            failure_class="unexpected_keyword",
            log="TypeError",
            files={},
        )
    )
    assert proposal.abstain
    assert "hosted_not_configured" in proposal.abstain_reason
    assert proposal.counts_as_model_call is False


def test_cpu_model_reports_unavailable_without_a_file(tmp_path: Path):
    missing = CpuProposer(tmp_path / "missing.gguf")
    assert missing.status().startswith("unavailable")


def test_workspace_path_cannot_escape(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    assert resolve_inside(tmp_path, "src/app.py").name == "app.py"
    with pytest.raises(PermissionError):
        resolve_inside(tmp_path, "../pyproject.toml")


def test_mcp_tools_stay_inside_the_workspace(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("urllib3==1.26.20\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("method_whitelist = 1\n", encoding="utf-8")
    context = {"root": tmp_path, "allow_network": False}
    listed = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, context)
    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert "run_tests" in names and "classify_failure" in names
    deps = handle(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_dependencies", "arguments": {}}},
        context,
    )
    assert '"urllib3"' in deps["result"]["content"][0]["text"]
    escaped = handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "read_file", "arguments": {"path": "../pyproject.toml"}},
        },
        context,
    )
    assert "error" in escaped
    metadata = handle(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "package_metadata", "arguments": {"name": "urllib3"}},
        },
        context,
    )
    assert "disabled" in metadata["result"]["content"][0]["text"]


def test_replacements_reject_an_empty_patch():
    reasons = validate_replacements({}, [], trusted=True, suspects=set())
    assert reasons == ["empty patch"]
