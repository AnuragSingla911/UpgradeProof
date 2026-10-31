"""Command line for one Java upgrade and for the local chat page."""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from upgradeproof.cases import load_case
from upgradeproof.harness import Budget, investigate, prepare_case
from upgradeproof.java_session import JavaSession
from upgradeproof.journey import journey_markdown
from upgradeproof.proposers import PromptProposer
from upgradeproof.report import evidence_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="upgradeproof")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="upgrade one local case folder with a prompt")
    run_cmd.add_argument("--input", type=Path, required=True)
    run_cmd.add_argument("--output", type=Path, required=True)
    run_cmd.add_argument("--prompt", type=Path, required=True)

    chat_cmd = sub.add_parser("chat", help="open the local page that accepts a GitHub URL and a prompt")
    chat_cmd.add_argument("--host", default="127.0.0.1")
    chat_cmd.add_argument("--port", type=int, default=8765)

    args = parser.parse_args(argv)
    if args.command == "run":
        return _run_prompt(args)
    if args.command == "chat":
        from upgradeproof.chat import serve

        serve(args.host, args.port)
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
