"""Command line for a single investigation and for the feasibility benchmark."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from dataclasses import asdict

from upgradeproof.benchmark import expectations_met, render_summary, run_benchmark
from upgradeproof.cases import load_case
from upgradeproof.harness import Budget, investigate, prepare_case
from upgradeproof.java_session import JavaSession
from upgradeproof.journey import journey_markdown
from upgradeproof.knowledge import PromoteError, promote_skill
from upgradeproof.proposers import CpuProposer, HostedProposer, PromptProposer, RulesProposer, SkillProposer
from upgradeproof.report import evidence_markdown
from upgradeproof.session import VenvSession


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="upgradeproof")
    sub = parser.add_subparsers(dest="command", required=True)

    investigate_cmd = sub.add_parser("investigate", help="investigate one case directory")
    investigate_cmd.add_argument("case", type=Path)
    investigate_cmd.add_argument("--mode", choices=("rules", "skill", "cpu", "hosted"), default="rules")
    investigate_cmd.add_argument("--rules-dir", type=Path, default=Path("rules/promoted"))
    investigate_cmd.add_argument("--skills-dir", type=Path, default=Path("skills"))
    investigate_cmd.add_argument("--out", type=Path, default=Path("artifacts"))

    benchmark = sub.add_parser("benchmark", help="run the feasibility suite")
    benchmark.add_argument("--root", type=Path, default=Path("."))
    benchmark.add_argument("--out", type=Path, default=Path("docs"))
    benchmark.add_argument("--cpu", action="store_true", help="run the optional local GGUF model")

    run_cmd = sub.add_parser("run", help="run one input folder with a prompt into an output folder")
    run_cmd.add_argument("--input", type=Path, required=True, help="case directory, for example test-data/java-acl")
    run_cmd.add_argument("--output", type=Path, required=True, help="directory that receives the evidence and journey")
    run_cmd.add_argument("--prompt", type=Path, required=True, help="operator prompt; only an upgradeproof-repair fence is executable")

    promote = sub.add_parser("promote", help="promote a verified skill fence into a rule")
    promote.add_argument("skill", type=Path)
    promote.add_argument("--verdict", required=True)
    promote.add_argument("--rules-dir", type=Path, required=True)
    promote.add_argument("--accept", action="store_true")

    sub.add_parser("mcp", help="serve the bounded tool surface on stdin/stdout")

    args = parser.parse_args(argv)
    if args.command == "run":
        return _run_prompt(args)
    if args.command == "investigate":
        return _investigate(args)
    if args.command == "benchmark":
        return _benchmark(args)
    if args.command == "promote":
        return _promote(args)
    if args.command == "mcp":
        from upgradeproof.mcp_server import serve

        serve(Path.cwd())
        return 0
    return 2


def _run_prompt(args) -> int:
    prompt_text = args.prompt.read_text(encoding="utf-8")
    case = load_case(args.input, cohort="prompt", modes=("prompt",))
    args.output.mkdir(parents=True, exist_ok=True)
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
            PromptProposer(prompt_text),
            mode="prompt",
            budget=Budget(case_timeout_seconds=case.timeout_seconds),
            expected=case.expected.get("prompt"),
        )
        oracle_isolated = "ORACLE_ONLY_BEHAVIOR" not in "\n".join(session.snapshot().values())
        command_log = list(session.command_log)
    report = evidence_markdown(evidence)
    journey = journey_markdown(
        evidence,
        prompt_text=prompt_text,
        input_dir=str(args.input),
        output_dir=str(args.output),
        command_log=command_log,
        oracle_isolated=oracle_isolated,
    )
    (args.output / "evidence.md").write_text(report, encoding="utf-8")
    (args.output / "journey.md").write_text(journey, encoding="utf-8")
    (args.output / "patch.diff").write_text(evidence.patch or "", encoding="utf-8")
    payload = asdict(evidence)
    payload["oracle_isolated"] = oracle_isolated
    payload["commands"] = command_log
    (args.output / "result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(journey)
    return 0 if evidence.expectation_met is not False else 1


def _investigate(args) -> int:
    case = load_case(args.case, cohort="ad-hoc", modes=(args.mode,))
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="upgradeproof-") as tmp:
        session = VenvSession(
            case.project_dir,
            case.oracle_dir,
            Path(tmp),
            timeout=case.timeout_seconds,
            requirement_name=case.requirement_name,
            to_version=case.to_version,
            install_project=case.install_project,
        )
        prepared = prepare_case(case, session, Budget(case_timeout_seconds=case.timeout_seconds))
        evidence = investigate(
            prepared,
            _proposer(args.mode, args.rules_dir, args.skills_dir),
            mode=args.mode,
            budget=Budget(case_timeout_seconds=case.timeout_seconds),
            expected=case.expected.get(args.mode),
        )
    report = evidence_markdown(evidence)
    (args.out / f"{case.id}.md").write_text(report, encoding="utf-8")
    if evidence.patch:
        (args.out / f"{case.id}.diff").write_text(evidence.patch, encoding="utf-8")
    print(report)
    return 0 if evidence.expectation_met is not False else 1


def _benchmark(args) -> int:
    document = run_benchmark(args.root.resolve(), args.out.resolve(), include_cpu=args.cpu)
    summary = render_summary(document)
    print(summary)
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as handle:
            handle.write(summary)
    ok = expectations_met(document)
    print(json.dumps({"ok": ok, "elapsed_seconds": document["elapsed_seconds"]}))
    return 0 if ok else 1


def _promote(args) -> int:
    try:
        target = promote_skill(
            args.skill.read_text(encoding="utf-8"),
            args.rules_dir,
            accept=args.accept,
            evidence_verdict=args.verdict,
        )
    except PromoteError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(target)
    return 0


def _proposer(mode: str, rules_dir: Path, skills_dir: Path):
    if mode == "rules":
        return RulesProposer.from_directory(rules_dir)
    if mode == "skill":
        return SkillProposer.from_directory(skills_dir)
    if mode == "cpu":
        raw = os.environ.get("UPGRADEPROOF_GGUF")
        return CpuProposer(Path(raw) if raw else None)
    if mode == "hosted":
        return HostedProposer()
    raise ValueError(mode)
