"""Clone a public GitHub Java 11 app, repair it for JDK 17, and publish ``java-17/``."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path

from upgradeproof.cases import Case
from upgradeproof.harness import Budget, investigate, prepare_case
from upgradeproof.java_session import JavaSession
from upgradeproof.journey import journey_markdown
from upgradeproof.proposers import PromptProposer
from upgradeproof.report import evidence_markdown

_GITHUB = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")


def parse_github_url(url: str) -> tuple[str, str]:
    match = _GITHUB.match(url.strip())
    if match is None:
        raise ValueError("repository must be an https://github.com/owner/name URL")
    return match.group(1), match.group(2)


def find_java11_project(clone: Path) -> Path:
    candidate = clone / "java-11"
    if (candidate / "requirements.txt").is_file() and (candidate / "src").is_dir():
        return candidate
    if (clone / "requirements.txt").is_file() and (clone / "src").is_dir():
        return clone
    raise ValueError("repository has no java-11 application (requirements.txt and src/)")


def upgrade_repository(url: str, prompt: str, *, push: bool = True, work_dir: Path | None = None) -> dict:
    """Clone ``url``, upgrade its Java 11 app to 17, and optionally push ``java-17/``."""

    owner, repo = parse_github_url(url)
    cleanup = work_dir is None
    root = work_dir or Path(tempfile.mkdtemp(prefix="upgradeproof-github-"))
    clone = root / "repo"
    try:
        _git(["clone", "--depth", "1", f"https://github.com/{owner}/{repo}.git", str(clone)])
        return upgrade_checkout(clone, prompt, push=push, page_url=f"https://github.com/{owner}/{repo}")
    finally:
        if cleanup and root.exists():
            shutil.rmtree(root, ignore_errors=True)


def upgrade_checkout(clone: Path, prompt: str, *, push: bool, page_url: str) -> dict:
    project = find_java11_project(clone)
    case = Case(
        id=clone.name,
        title="JDK 11 to 17",
        package="jdk",
        requirement_name="java",
        from_version="11",
        to_version="17",
        project_dir=project,
        oracle_dir=project / "oracle",
        root=clone,
        expected={},
        install_project=False,
        timeout_seconds=120,
        cohort="github",
        modes=("prompt",),
    )
    with tempfile.TemporaryDirectory(prefix="upgradeproof-java-") as tmp:
        session = JavaSession(
            case.project_dir,
            case.oracle_dir,
            Path(tmp),
            timeout=case.timeout_seconds,
            requirement_name=case.requirement_name,
            to_version=case.to_version,
            from_version=case.from_version,
        )
        prepared = prepare_case(case, session, Budget(case_timeout_seconds=case.timeout_seconds))
        evidence = investigate(
            prepared,
            PromptProposer(prompt),
            mode="prompt",
            budget=Budget(case_timeout_seconds=case.timeout_seconds),
        )
        journey = journey_markdown(
            evidence,
            prompt_text=prompt,
            input_dir=page_url,
            output_dir=str(clone / "java-17"),
            command_log=list(session.command_log),
            oracle_isolated=True,
        )
        pushed = False
        publish_error = ""
        if evidence.verified:
            session.write_tree(clone / "java-17")
            (clone / "journey.md").write_text(journey, encoding="utf-8")
            (clone / "evidence.md").write_text(evidence_markdown(evidence), encoding="utf-8")
            if push:
                try:
                    _commit_and_push(clone)
                    pushed = True
                except RuntimeError as exc:
                    publish_error = str(exc)
    payload = asdict(evidence)
    payload["journey"] = journey
    payload["repository"] = page_url
    payload["pushed"] = pushed
    payload["publish_error"] = publish_error
    payload["java_17"] = str(clone / "java-17") if evidence.verified else ""
    return payload


def _commit_and_push(clone: Path) -> None:
    _git(["add", "java-17", "journey.md", "evidence.md"], cwd=clone)
    status = _git(["status", "--porcelain"], cwd=clone)
    if not status.strip():
        return
    _git(["commit", "-m", "Add the Java 17 repair verified by UpgradeProof."], cwd=clone)
    _git(["push", "origin", "HEAD"], cwd=clone)


def _git(args: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"git {' '.join(args)} failed")
    return completed.stdout
