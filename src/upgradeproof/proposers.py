"""Match every known repair whose error class appears in the compiler log."""

from __future__ import annotations

from pathlib import Path

from upgradeproof.checks import failure_classes
from upgradeproof.knowledge import RepairRule, extract_skill_fences, load_rule_toml
from upgradeproof.model import Proposal, ProposalRequest, Replacement

_SKILLS = Path(__file__).resolve().parents[2] / "skills"


class PromptProposer:
    """Use fences from the prompt and from ``skills/``.

    The prompt states the upgrade. Each fence covers one error class and the
    source text it knows. A compiler diagnostic with no fence stays unresolved.
    """

    def __init__(self, prompt_text: str, skills_dir: Path | None = None):
        self.prompt_text = prompt_text
        self.rules: list[RepairRule] = []
        self.fence_error = ""
        self.rules.extend(_rules_from(prompt_text, source="prompt"))
        root = skills_dir if skills_dir is not None else _SKILLS
        if root.is_dir():
            for path in sorted(root.glob("*/SKILL.md")):
                self.rules.extend(_rules_from(path.read_text(encoding="utf-8"), source="skill"))
        if not self.rules:
            self.fence_error = "no upgradeproof-repair fences in the prompt or skills"

    def propose(self, request: ProposalRequest) -> Proposal:
        if not self.rules:
            return Proposal.abstention("prompt", self.fence_error or "prompt has no executable repair")
        return _propose_from_rules(self.rules, request)


def _rules_from(markdown: str, *, source: str) -> list[RepairRule]:
    rules: list[RepairRule] = []
    for body in extract_skill_fences(markdown):
        try:
            rules.append(load_rule_toml(body, source=source))
        except (ValueError, KeyError):
            continue
    return rules


def _propose_from_rules(rules: list[RepairRule], request: ProposalRequest) -> Proposal:
    log = request.log if not request.feedback else f"{request.log}\n{request.feedback}"
    classes = set(failure_classes(log))
    if request.failure_class:
        classes.add(request.failure_class)
    candidates = [
        rule
        for rule in rules
        if rule.matches(package=request.package, failure_class=request.failure_class, log=log, failure_classes=classes)
    ]
    applied: list[Replacement] = []
    seen: set[tuple[str, str, str]] = set()
    used: list[RepairRule] = []
    used_ids: set[str] = set()
    for rule in candidates:
        if rule.id in used_ids:
            continue
        materialized = rule.materialize(request.files)
        if not materialized:
            continue
        used_ids.add(rule.id)
        used.append(rule)
        for item in materialized:
            key = (item.path, item.old, item.new)
            if key in seen:
                continue
            seen.add(key)
            applied.append(item)
    if applied:
        return Proposal(
            source="+".join(f"{rule.source}:{rule.id}" for rule in used),
            replacements=tuple(applied),
            rationale="Matched " + ", ".join(rule.id for rule in used) + ".",
            trusted=True,
        )
    if candidates:
        return Proposal.abstention("repair", "a repair matched the error class but not the source text")
    shown = ", ".join(sorted(classes)) or "unknown"
    return Proposal.abstention("repair", f"no repair covers {shown}")
