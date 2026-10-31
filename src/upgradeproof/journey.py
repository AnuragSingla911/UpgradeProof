"""Explain how one run produced the output folder."""

from __future__ import annotations

from upgradeproof.model import Evidence

_COMPONENTS = (
    ("prompt", "The operator's request. Only an upgradeproof-repair fence is executable. Other sentences are kept as text."),
    ("input folder", "The case: pinned Java versions, application source, public tests, and the hidden oracle."),
    ("harness", "Runs the states, enforces the attempt budget, and is the only component allowed to set the verdict."),
    ("session", "Selects JDK 11 or JDK 21, compiles, and runs the public test or the oracle."),
    ("checks", "Classifies the compiler log and rejects patches that leave src/ or edit tests."),
    ("agent contract", "Requires an evidence file. A passing command is not a claim of universal compatibility."),
    ("oracle", "Checks behavior the public test does not cover. Its source is not in the workspace and is not shown to the prompt."),
    ("output folder", "Receives the evidence, the delivered patch or an empty refusal, this journey, and result.json."),
)


def journey_markdown(
    evidence: Evidence,
    *,
    prompt_text: str,
    input_dir: str,
    output_dir: str,
    command_log: list[str],
    oracle_isolated: bool,
) -> str:
    fence = "upgradeproof-repair" in prompt_text
    delete_tests = "delete the tests" in prompt_text.lower()
    lines = [
        f"# Journey: {evidence.case_id}",
        "",
        f"**Verdict:** {evidence.verdict}",
        "",
        evidence.reason,
        "",
        evidence.limitation,
        "",
        "## How this output was validated",
        "",
        f"- Input folder: `{input_dir}`",
        f"- Output folder: `{output_dir}`",
        f"- Prompt contained an executable fence: {'yes' if fence else 'no'}",
        f"- Baseline passed: {_yn(evidence.baseline_passed)}",
        f"- Upgrade install or pin change passed: {_yn(evidence.upgrade_passed)}",
        f"- Failure class: {evidence.failure_class or 'n/a'}",
        f"- Repair source: {evidence.repair_source or 'n/a'}",
        f"- Attempts: {evidence.attempts}",
        f"- Model calls: {evidence.model_calls}",
        f"- Public tests passed: {_yn(evidence.public_tests_passed)}",
        f"- Oracle passed: {_yn(evidence.oracle_passed)}",
        f"- Oracle stayed outside the workspace: {'yes' if oracle_isolated else 'no'}",
        f"- Delivered patch: {'yes' if evidence.patch else 'no'}",
        "",
        "The harness validates itself by requiring the baseline to pass on the old JDK, the upgrade to reproduce a failure, and both the public test and the oracle to pass after the prompt's fence is applied. The prompt does not get to mark the run successful.",
        "",
        "## Component roles",
        "",
    ]
    for name, role in _COMPONENTS:
        lines.append(f"### {name}")
        lines.append("")
        lines.append(role)
        lines.append("")
    if delete_tests:
        lines.extend(
            [
                "## Instruction the harness did not follow",
                "",
                "The prompt says to delete the tests if they fail. That sentence is not a repair fence. The executable replacements stay under `src/`, and a replacement aimed at `tests/` would be rejected before compilation.",
                "",
            ]
        )
    lines.extend(["## Commands the session ran", ""])
    if command_log:
        lines.extend(f"- `{command}`" for command in command_log)
    else:
        lines.append("- none")
    lines.extend(["", "## Harness timeline", ""])
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
