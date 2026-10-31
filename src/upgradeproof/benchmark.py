"""Run the feasibility suite and write a results document."""

from __future__ import annotations

import json
import platform
import shutil
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ASIA_CALCUTTA = timezone(timedelta(hours=5, minutes=30))

from upgradeproof import __version__
from upgradeproof.cases import Case, load_case, load_suite
from upgradeproof.guards import run_guard_checks
from upgradeproof.harness import Budget, investigate, prepare_case
from upgradeproof.knowledge import extract_skill_fence, promote_skill
from upgradeproof.model import Proposal, Replacement
from upgradeproof.proposers import CpuProposer, FixedProposer, RulesProposer, SkillProposer
from upgradeproof.report import evidence_markdown
from upgradeproof.session import VenvSession

_SENTINEL = "ORACLE_ONLY_BEHAVIOR"


def default_rules_dir(repo_root: Path) -> Path:
    return repo_root / "rules" / "promoted"


def default_skills_dir(repo_root: Path) -> Path:
    return repo_root / "skills"


def run_benchmark(repo_root: Path, output_dir: Path, *, include_cpu: bool = False) -> dict:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = output_dir / "evidence"
    if evidence_dir.exists():
        shutil.rmtree(evidence_dir)
    evidence_dir.mkdir(parents=True)
    rules_dir = default_rules_dir(repo_root)
    skills_dir = default_skills_dir(repo_root)
    rows: list[dict] = []
    probes: list[dict] = []
    isolation: list[dict[str, object]] = []

    for case in load_suite(repo_root):
        with tempfile.TemporaryDirectory(prefix=f"upgradeproof-{case.id}-") as tmp:
            session = _session(case, Path(tmp))
            prepared = prepare_case(case, session, Budget(case_timeout_seconds=case.timeout_seconds))
            snapshot = "\n".join(session.snapshot().values())
            isolation.append(
                {
                    "case_id": case.id,
                    "ok": _SENTINEL not in snapshot and not (session.root / "oracle").exists(),
                }
            )
            for mode in case.modes:
                proposer = _proposer(mode, rules_dir, skills_dir)
                evidence = investigate(
                    prepared,
                    proposer,
                    mode=mode,
                    budget=Budget(case_timeout_seconds=case.timeout_seconds),
                    expected=case.expected.get(mode),
                )
                _write_evidence(evidence_dir, evidence)
                record = asdict(evidence)
                record["cohort"] = case.cohort
                rows.append(record)
            probes.extend(_probes_for(case, prepared, evidence_dir))
    promotion = _promotion(repo_root, skills_dir, evidence_dir)
    guards = run_guard_checks()
    cpu = _cpu_arm(repo_root, include_cpu=include_cpu)
    elapsed = round(time.perf_counter() - started, 3)
    document = {
        "project": "UpgradeProof",
        "version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_at_asia_calcutta": datetime.now(_ASIA_CALCUTTA).strftime("%Y-%m-%d %H:%M Asia/Calcutta"),
        "python": platform.python_version(),
        "elapsed_seconds": elapsed,
        "limitation": (
            "These fixtures were written for this repository. Promoted rules were "
            "authored with the cases, so the repair rate is a feasibility result, "
            "not an estimate for unseen upgrades. A passing oracle is not universal "
            "compatibility."
        ),
        "rows": rows,
        "probes": probes,
        "guards": guards,
        "promotion": promotion,
        "isolation": isolation,
        "cpu_model": cpu,
        "metrics": _metrics(rows),
    }
    serialized = json.dumps(document, indent=2) + "\n"
    (output_dir / "results.json").write_text(serialized, encoding="utf-8")
    (output_dir / "results.js").write_text(
        "window.UPGRADEPROOF_RESULTS = " + json.dumps(document) + ";\n",
        encoding="utf-8",
    )
    summary = render_summary(document)
    (output_dir / "summary.md").write_text(summary, encoding="utf-8")
    return document


def render_summary(document: dict) -> str:
    lines = [
        "# UpgradeProof feasibility results",
        "",
        f"Generated {document['generated_at_asia_calcutta']}. Elapsed {document['elapsed_seconds']}s.",
        "",
        document["limitation"],
        "",
        "## Cases",
        "",
        "Row times each include that case's environment setup. Two modes share the setup, so those times are not additive. `elapsed_seconds` is the wall clock for the whole command.",
        "",
        "| Case | Cohort | Mode | Verdict | Model calls | Seconds | Expectation |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for row in document["rows"]:
        met = "met" if row["expectation_met"] else "MISSED"
        lines.append(
            f"| {row['case_id']} | {row.get('cohort', '')} | {row['mode']} | {row['verdict']} | {row['model_calls']} | {row['wall_clock_seconds']} | {met} |"
        )
    lines.extend(["", "## Metrics", ""])
    for cohort, metrics in document["metrics"].items():
        lines.append(
            f"- **{cohort}**: {metrics['expectations_met']}/{metrics['runs']} expectations met, "
            f"{metrics['verified']}/{metrics['runs']} verified verdicts, "
            f"{metrics['regressions']} delivered regressions, "
            f"{metrics['model_calls']} model calls, "
            f"cost/verified USD {metrics['cost_per_verified_repair']}"
        )
    lines.extend(["", "## Execution probes", ""])
    for probe in document["probes"]:
        flag = "pass" if probe["ok"] else "FAIL"
        lines.append(f"- {flag}: {probe['name']} → {probe['verdict']} ({probe['reason']})")
    lines.extend(["", "## Guard checks", ""])
    for guard in document["guards"]:
        flag = "pass" if guard["ok"] else "FAIL"
        lines.append(f"- {flag}: {guard['name']} → {guard['verdict']}")
    promotion = document["promotion"]
    lines.extend(
        [
            "",
            "## Promotion",
            "",
            f"- First encounter: {promotion.get('first_source')} verified={promotion.get('first_verified')} model_calls={promotion.get('first_model_calls')}",
            f"- Maintainer accepted: {promotion.get('accepted')}",
            f"- Later encounter: {promotion.get('later_source')} verified={promotion.get('later_verified')} model_calls={promotion.get('later_model_calls')}",
            "",
            "## CPU model",
            "",
            f"- Status: {document['cpu_model']['status']}",
            "",
        ]
    )
    return "\n".join(lines)


def expectations_met(document: dict) -> bool:
    if any(not row["expectation_met"] for row in document["rows"]):
        return False
    if any(not item["ok"] for item in document["probes"]):
        return False
    if any(not item["ok"] for item in document["guards"]):
        return False
    if any(not item["ok"] for item in document["isolation"]):
        return False
    promotion = document["promotion"]
    return bool(promotion.get("ok"))


def _session(case: Case, work_dir: Path) -> VenvSession:
    return VenvSession(
        case.project_dir,
        case.oracle_dir,
        work_dir,
        timeout=case.timeout_seconds,
        requirement_name=case.requirement_name,
        to_version=case.to_version,
        install_project=case.install_project,
    )


def _proposer(mode: str, rules_dir: Path, skills_dir: Path):
    if mode == "rules":
        return RulesProposer.from_directory(rules_dir)
    if mode == "skill":
        return SkillProposer.from_directory(skills_dir)
    if mode == "cpu":
        return CpuProposer(_gguf_path())
    raise ValueError(f"unsupported benchmark mode {mode}")


def _probes_for(case: Case, prepared, evidence_dir: Path) -> list[dict]:
    probes: list[dict] = []
    if case.id == "urllib3-retry":
        proposal = Proposal(
            source="model:scripted",
            replacements=(
                Replacement("src/retryctx/client.py", "method_whitelist=", "allowed_methodz="),
            ),
            counts_as_model_call=True,
            trusted=True,
            rationale="Use a keyword that does not exist.",
        )
        evidence = investigate(prepared, FixedProposer(proposal), mode="probe-invented-api", budget=Budget())
        _write_evidence(evidence_dir, evidence)
        probes.append(
            {
                "name": "invented urllib3 keyword is caught by execution",
                "ok": evidence.verdict == "unresolved" and "tests_still_failing" in evidence.reason and not evidence.patch,
                "verdict": evidence.verdict,
                "reason": evidence.reason,
                "model_calls": evidence.model_calls,
            }
        )
        return probes
    if case.id == "packaging-legacy-version":
        original = prepared.session.base_files["src/versions/describe.py"]
        weak = (
            "from packaging.version import parse\n\n\n"
            "def describe(version: str) -> str:\n"
            "    parsed = parse(version)\n"
            '    return f"pep440:{parsed}"\n'
        )
        proposal = Proposal(
            source="model:scripted",
            replacements=(Replacement("src/versions/describe.py", original, weak),),
            counts_as_model_call=True,
            trusted=True,
            rationale="Drop legacy-version handling.",
        )
        evidence = investigate(prepared, FixedProposer(proposal), mode="probe-weak-repair", budget=Budget())
        _write_evidence(evidence_dir, evidence)
        probes.append(
            {
                "name": "packaging repair that passes public tests but fails the oracle is not delivered",
                "ok": (
                    evidence.verdict == "unresolved"
                    and evidence.reason == "oracle_failed"
                    and evidence.public_tests_passed is True
                    and evidence.patch == ""
                ),
                "verdict": evidence.verdict,
                "reason": evidence.reason,
                "model_calls": evidence.model_calls,
            }
        )
        return probes
    return []


def _promotion(repo_root: Path, skills_dir: Path, evidence_dir: Path) -> dict:
    variant = load_case(
        repo_root / "cases" / "promotion" / "urllib3_gateway",
        cohort="promotion",
        modes=("rules",),
    )
    skill_text = (skills_dir / "urllib3" / "SKILL.md").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="upgradeproof-promote-") as tmp:
        work = Path(tmp)
        session = _session(variant, work / "ws")
        # The first encounter is a scripted proposer standing in for a model
        # that has already been shown the migration. It is not a neural model.
        first_proposal = Proposal(
            source="model:scripted-first-encounter",
            replacements=(Replacement("src/retryctx/gateway.py", "method_whitelist=", "allowed_methods="),),
            counts_as_model_call=True,
            trusted=True,
            rationale="Rename the removed Retry keyword.",
        )
        prepared = prepare_case(variant, session, Budget())
        first = investigate(prepared, FixedProposer(first_proposal), mode="promotion-first", budget=Budget())
        _write_evidence(evidence_dir, first)
        rules_dir = work / "promoted"
        try:
            promoted = promote_skill(
                skill_text,
                rules_dir,
                accept=bool(first.verified),
                evidence_verdict=first.verdict,
            )
            accepted = True
            promote_error = ""
        except Exception as exc:  # noqa: BLE001
            promoted = None
            accepted = False
            promote_error = str(exc)
        later = None
        if promoted is not None:
            later = investigate(
                prepared,
                RulesProposer.from_directory(rules_dir),
                mode="promotion-later",
                budget=Budget(),
            )
            _write_evidence(evidence_dir, later)
        fence_present = extract_skill_fence(skill_text) is not None
        later_ok = (
            later is not None
            and later.verified
            and later.model_calls == 0
            and later.repair_source == "rule:urllib3-retry-method-whitelist"
        )
        return {
            "ok": bool(first.verified and first.model_calls == 1 and accepted and later_ok and fence_present),
            "accepted": accepted,
            "promote_error": promote_error,
            "first_source": first.repair_source,
            "first_verified": first.verified,
            "first_model_calls": first.model_calls,
            "first_verdict": first.verdict,
            "later_source": None if later is None else later.repair_source,
            "later_verified": None if later is None else later.verified,
            "later_model_calls": None if later is None else later.model_calls,
            "later_verdict": None if later is None else later.verdict,
            "promoted_rule": None if promoted is None else promoted.name,
        }


def _cpu_arm(repo_root: Path, *, include_cpu: bool) -> dict:
    proposer = CpuProposer(_gguf_path())
    status = proposer.status()
    if not include_cpu:
        return {"status": status, "ran": False, "rows": []}
    if status != "ready":
        return {"status": status, "ran": False, "rows": []}
    rows = []
    rules_cases = [case for case in load_suite(repo_root) if case.cohort == "repair"]
    for case in rules_cases:
        with tempfile.TemporaryDirectory(prefix=f"upgradeproof-cpu-{case.id}-") as tmp:
            session = _session(case, Path(tmp))
            prepared = prepare_case(case, session, Budget(case_timeout_seconds=case.timeout_seconds))
            evidence = investigate(prepared, proposer, mode="cpu", budget=Budget(max_model_calls=2))
            rows.append(
                {
                    "case_id": case.id,
                    "verdict": evidence.verdict,
                    "model_calls": evidence.model_calls,
                    "reason": evidence.reason,
                    "wall_clock_seconds": evidence.wall_clock_seconds,
                }
            )
    verified = sum(1 for row in rows if row["verdict"] == "verified_repair")
    return {"status": "ready", "ran": True, "verified": verified, "runs": len(rows), "rows": rows}


def _gguf_path() -> Path | None:
    import os

    raw = os.environ.get("UPGRADEPROOF_GGUF")
    if raw:
        return Path(raw)
    return None


def _write_evidence(directory: Path, evidence) -> None:
    name = f"{evidence.case_id}--{evidence.mode}.md"
    (directory / name).write_text(evidence_markdown(evidence), encoding="utf-8")
    if evidence.patch:
        (directory / f"{evidence.case_id}--{evidence.mode}.diff").write_text(evidence.patch, encoding="utf-8")


def _metrics(rows: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        key = f"{row.get('cohort', 'case')}/{row['mode']}"
        grouped.setdefault(key, []).append(row)
    summary = {}
    for mode, items in grouped.items():
        verified = [item for item in items if item["verdict"] in {"verified_repair", "verified_bump"}]
        regressions = [
            item
            for item in items
            if item["patch"] and item["verdict"] not in {"verified_repair", "verified_bump"}
        ]
        calls = sum(item["model_calls"] for item in items)
        cost = sum(item["estimated_cost_usd"] for item in items)
        summary[mode] = {
            "runs": len(items),
            "expectations_met": sum(1 for item in items if item["expectation_met"]),
            "verified": len(verified),
            "verified_success_rate": round(len(verified) / len(items), 3) if items else None,
            "regressions": len(regressions),
            "model_calls": calls,
            "estimated_cost_usd": round(cost, 6),
            "cost_per_verified_repair": None if not verified else round(cost / len(verified), 6),
            "wall_clock_seconds_sum_including_shared_setup": round(
                sum(item["wall_clock_seconds"] for item in items), 3
            ),
        }
    return summary
