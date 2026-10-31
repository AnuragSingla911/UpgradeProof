"""Evidence reports rendered for humans and for the results table."""

from __future__ import annotations

from upgradeproof.model import Evidence


def evidence_markdown(evidence: Evidence) -> str:
    patch = evidence.patch.strip() or "(no delivered patch)"
    rejections = "\n".join(f"- {item}" for item in evidence.rejections) or "- none"
    lines = [
        f"# {evidence.case_id} ({evidence.mode})",
        "",
        f"**Verdict:** {evidence.verdict}",
        "",
        evidence.reason,
        "",
        evidence.limitation,
        "",
        "## Run",
        "",
        f"- Title: {evidence.title}",
        f"- Failure class: {evidence.failure_class or 'n/a'}",
        f"- Repair source: {evidence.repair_source or 'n/a'}",
        f"- Attempts: {evidence.attempts}",
        f"- Model calls: {evidence.model_calls}",
        f"- Estimated cost (USD): {evidence.estimated_cost_usd:.4f}",
        f"- Wall clock, including shared setup (seconds): {evidence.wall_clock_seconds:.3f}",
        f"- Baseline passed: {_yn(evidence.baseline_passed)}",
        f"- Upgrade install passed: {_yn(evidence.upgrade_passed)}",
        f"- Public tests passed: {_yn(evidence.public_tests_passed)}",
        f"- Oracle passed: {_yn(evidence.oracle_passed)}",
        "",
        "## Patch rejections",
        "",
        rejections,
        "",
        "## Delivered patch",
        "",
        "```diff",
        patch,
        "```",
        "",
        "## Timeline",
        "",
    ]
    for event in evidence.timeline:
        state = event.get("state")
        detail = {key: value for key, value in event.items() if key not in {"state", "output"}}
        lines.append(f"- `{state}` {detail}")
    lines.append("")
    return "\n".join(lines)


def _yn(value: bool | None) -> str:
    if value is None:
        return "not run"
    return "yes" if value else "no"
