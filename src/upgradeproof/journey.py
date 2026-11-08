"""Explain how one run produced the output folder."""

from __future__ import annotations

from upgradeproof.model import Evidence

_COMPONENTS = (
    ("prompt", "The upgrade request. Repairs come from fences in the prompt or the JDK skill. Each fence covers one error class. Other sentences are not executed."),
    ("input folder", "The case: pinned Java versions, application source, public tests, and the hidden oracle."),
    ("harness", "Runs the states, enforces the attempt budget, and is the only component allowed to set the verdict."),
    ("session", "Selects the JDK named by the pin, compiles, and runs the public test or the oracle."),
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
    fence_in_prompt = "```upgradeproof-repair" in prompt_text
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
        f"- Prompt contained upgradeproof-repair fences: {'yes' if fence_in_prompt else 'no'}",
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
        _validation_summary(evidence, fence_in_prompt),
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


def _validation_summary(evidence: Evidence, fence_in_prompt: bool) -> str:
    parts = [
        "The harness requires the baseline to pass on the old JDK, the pin change to succeed, and the failure to be reproduced before any repair.",
    ]
    if evidence.oracle_passed is None:
        parts.append("With no oracle on disk, verification ends when public tests pass after a repair or bump.")
    else:
        parts.append("When an oracle is supplied, it must pass after public tests pass.")
    if evidence.repair_source and evidence.repair_source.startswith("prompt:"):
        parts.append("Repairs came from a fence in the prompt text.")
    elif evidence.repair_source and "skill:" in evidence.repair_source:
        parts.append("Repairs came from the bundled skills (see `repair_source` in result.json).")
    elif evidence.repair_source == "harness:version-bump":
        parts.append("No source repair was needed beyond the pin change.")
    if fence_in_prompt and evidence.repair_source and evidence.repair_source.startswith("skill:"):
        parts.append("The prompt stated the upgrade; executable fences in the prompt were optional.")
    parts.append("The prompt does not get to mark the run successful.")
    return " ".join(parts)


def _yn(value: bool | None) -> str:
    if value is None:
        return "not run"
    return "yes" if value else "no"
