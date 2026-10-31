"""JDK 11 to 17 prompt experiment. The live compile skips when either JDK is absent."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from upgradeproof.checks import classify_failure, failure_classes, validate_replacements
from upgradeproof.cli import main
from upgradeproof.github_app import find_java11_project, parse_github_url, upgrade_checkout
from upgradeproof.model import ProposalRequest, Replacement
from upgradeproof.proposers import PromptProposer

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "test-data"


def _jdk_home(version: str) -> Path | None:
    override = os.environ.get(f"UPGRADEPROOF_JDK_{version}")
    candidates = [Path(override)] if override else []
    candidates.extend(
        [
            Path(f"/usr/lib/jvm/java-{version}-openjdk-amd64"),
            Path(f"/usr/lib/jvm/java-{version}-openjdk-arm64"),
        ]
    )
    for home in candidates:
        if (home / "bin" / "javac").is_file() and (home / "bin" / "java").is_file():
            return home
    return None


def test_github_url_and_java11_layout(tmp_path: Path):
    owner, repo = parse_github_url("https://github.com/AnuragSingla911/Java11to17UpgradeSample")
    assert (owner, repo) == ("AnuragSingla911", "Java11to17UpgradeSample")
    with pytest.raises(ValueError):
        parse_github_url("https://example.com/app")
    project = tmp_path / "java-11"
    project.mkdir()
    (project / "requirements.txt").write_text("java==11\n", encoding="utf-8")
    (project / "src").mkdir()
    assert find_java11_project(tmp_path) == project


def test_javac_missing_package_is_missing_symbol():
    log = "src/AccessLabel.java:3: error: package java.security.acl does not exist"
    assert classify_failure(log) == "missing_symbol"


def test_a_log_can_carry_more_than_one_error_class():
    log = "\n".join(
        [
            "src/AccessLabel.java:3: error: package java.security.acl does not exist",
            "src/AccessLabel.java:8: error: incompatible types: int cannot be converted to java.lang.String",
        ]
    )
    assert failure_classes(log) == ["missing_symbol", "incompatible_types"]


def test_general_prompt_repairs_only_the_class_the_skill_knows():
    source = (DATA / "java-11" / "src" / "AccessLabel.java").read_text(encoding="utf-8")
    proposer = PromptProposer((DATA / "chat-prompt.md").read_text(encoding="utf-8"))
    known = proposer.propose(
        ProposalRequest(
            case_id="sample",
            package="jdk",
            from_version="11",
            to_version="17",
            failure_class="missing_symbol",
            log="src/AccessLabel.java:3: error: package java.security.acl does not exist",
            files={"src/AccessLabel.java": source},
        )
    )
    assert known.abstain is False
    assert known.source == "skill:jdk-acl-removed"
    unknown = proposer.propose(
        ProposalRequest(
            case_id="sample",
            package="jdk",
            from_version="11",
            to_version="17",
            failure_class="incompatible_types",
            log="src/AccessLabel.java:8: error: incompatible types: int cannot be converted to java.lang.String",
            files={"src/AccessLabel.java": source},
        )
    )
    assert unknown.abstain is True
    assert "incompatible_types" in unknown.abstain_reason


def test_java_source_is_in_scope_when_trusted():
    files = {"src/AccessLabel.java": "        return java.security.acl.Acl.class.getSimpleName();\n"}
    reasons = validate_replacements(
        files,
        [Replacement("src/AccessLabel.java", "        return java.security.acl.Acl.class.getSimpleName();", '        return "Acl";')],
        trusted=True,
        suspects=set(),
    )
    assert reasons == []
    rejected = validate_replacements(
        {"tests/PublicTest.java": "throw new AssertionError(\"label\");\n"},
        [Replacement("tests/PublicTest.java", 'throw new AssertionError("label");', "System.out.println(1);")],
        trusted=True,
        suspects=set(),
    )
    assert any("protected test" in reason for reason in rejected)


def test_java_11_and_java_17_are_the_same_program():
    eleven = DATA / "java-11"
    seventeen = DATA / "java-17"
    assert (eleven / "requirements.txt").read_text(encoding="utf-8") == "java==11\n"
    assert (seventeen / "requirements.txt").read_text(encoding="utf-8") == "java==17\n"
    for relative in ("src/AccessLabel.java", "tests/PublicTest.java"):
        assert (eleven / relative).read_text(encoding="utf-8") == (seventeen / relative).read_text(encoding="utf-8")
    prompt = (DATA / "prompt.md").read_text(encoding="utf-8")
    assert "upgradeproof-repair" in prompt
    assert "delete the tests" in prompt
    assert "ORACLE_ONLY_BEHAVIOR" not in "\n".join(path.read_text(encoding="utf-8") for path in eleven.rglob("*.java"))
    assert not (eleven / "oracle").exists()
    assert not (seventeen / "oracle").exists()


def _compile_and_run(home: Path, release: str, project: Path, work: Path) -> subprocess.CompletedProcess[str]:
    classes = work / "classes"
    classes.mkdir(parents=True)
    sources = sorted(project.rglob("*.java"))
    compiled = subprocess.run(
        [str(home / "bin" / "javac"), "--release", release, "-d", str(classes), *[str(path) for path in sources]],
        text=True,
        capture_output=True,
        check=False,
    )
    if compiled.returncode != 0:
        return compiled
    return subprocess.run(
        [str(home / "bin" / "java"), "-cp", str(classes), "PublicTest"],
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.skipif(_jdk_home("11") is None or _jdk_home("17") is None, reason="JDK 11 and JDK 17 are required")
def test_prompt_run_writes_a_verified_journey(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    jdk11 = _jdk_home("11")
    jdk17 = _jdk_home("17")
    assert jdk11 is not None and jdk17 is not None
    passed = _compile_and_run(jdk11, "11", DATA / "java-11", tmp_path / "java-11")
    assert passed.returncode == 0, passed.stderr
    assert "public ok" in passed.stdout
    failed = _compile_and_run(jdk17, "17", DATA / "java-17", tmp_path / "java-17")
    assert failed.returncode != 0
    assert "java.security.acl" in failed.stderr

    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("UPGRADEPROOF_JDK_11", str(jdk11))
    monkeypatch.setenv("UPGRADEPROOF_JDK_17", str(jdk17))
    output = tmp_path / "out"
    code = main(
        [
            "run",
            "--input",
            "test-data",
            "--output",
            str(output),
            "--prompt",
            "test-data/prompt.md",
        ]
    )
    result = json.loads((output / "result.json").read_text(encoding="utf-8"))
    assert code == 0, result
    assert result["verdict"] == "verified_repair"
    assert result["model_calls"] == 0
    assert result["oracle_passed"] is True
    assert result["oracle_isolated"] is True
    assert result["repair_source"] == "prompt:jdk-acl-removed"
    journey = (output / "journey.md").read_text(encoding="utf-8")
    assert "Instruction the harness did not follow" in journey
    assert "Component roles" in journey
    assert "delete the tests" in journey
    patch = (output / "patch.diff").read_text(encoding="utf-8")
    assert "java==17" in patch
    assert 'return "Acl";' in patch
    assert "ORACLE_ONLY_BEHAVIOR" not in patch
    assert "tests/PublicTest.java" not in patch


@pytest.mark.skipif(_jdk_home("11") is None or _jdk_home("17") is None, reason="JDK 11 and JDK 17 are required")
def test_checkout_writes_java_17_and_leaves_java_11(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    jdk11 = _jdk_home("11")
    jdk17 = _jdk_home("17")
    assert jdk11 is not None and jdk17 is not None
    monkeypatch.setenv("UPGRADEPROOF_JDK_11", str(jdk11))
    monkeypatch.setenv("UPGRADEPROOF_JDK_17", str(jdk17))
    repo = tmp_path / "repo"
    shutil.copytree(DATA / "java-11", repo / "java-11")
    result = upgrade_checkout(
        repo,
        (DATA / "prompt.md").read_text(encoding="utf-8"),
        push=False,
        page_url="https://github.com/AnuragSingla911/Java11to17UpgradeSample",
    )
    assert result["verdict"] == "verified_repair"
    assert result["pushed"] is False
    assert (repo / "java-11" / "requirements.txt").read_text(encoding="utf-8") == "java==11\n"
    repaired = (repo / "java-17" / "src" / "AccessLabel.java").read_text(encoding="utf-8")
    assert 'return "Acl";' in repaired
    assert (repo / "java-17" / "requirements.txt").read_text(encoding="utf-8") == "java==17\n"
    assert (repo / "journey.md").is_file()
