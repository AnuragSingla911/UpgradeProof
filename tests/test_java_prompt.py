"""JDK 11 to 21 prompt experiment. Skips when either JDK is absent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from upgradeproof.checks import classify_failure, validate_replacements
from upgradeproof.cli import main
from upgradeproof.model import Replacement

ROOT = Path(__file__).resolve().parents[1]


def test_javac_missing_package_is_missing_symbol():
    log = "src/AccessLabel.java:3: error: package java.security.acl does not exist"
    assert classify_failure(log) == "missing_symbol"


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


@pytest.mark.skipif(
    not (Path("/usr/lib/jvm/java-11-openjdk-amd64/bin/javac").is_file() or Path("/usr/lib/jvm/java-11-openjdk-arm64/bin/javac").is_file())
    or not (Path("/usr/lib/jvm/java-21-openjdk-amd64/bin/javac").is_file() or Path("/usr/lib/jvm/java-21-openjdk-arm64/bin/javac").is_file()),
    reason="JDK 11 and JDK 21 are required",
)
def test_prompt_run_writes_a_verified_journey(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(ROOT)
    output = tmp_path / "out"
    code = main(
        [
            "run",
            "--input",
            "test-data/java-acl",
            "--output",
            str(output),
            "--prompt",
            "test-data/java-acl/prompt.md",
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
    assert "java==21" in patch
    assert 'return "Acl";' in patch
    assert "ORACLE_ONLY_BEHAVIOR" not in patch
    assert "tests/PublicTest.java" not in patch
