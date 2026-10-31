"""Load maintainer-authored repair rules and skill fences."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from upgradeproof.checks import _is_application_source
from upgradeproof.model import Replacement

_FENCE = "```upgradeproof-repair"


@dataclass(frozen=True)
class RepairRule:
    id: str
    package: str
    error_class: str
    error_contains: tuple[str, ...]
    replacements: tuple[dict[str, str], ...]
    source: str
    trusted: bool = True

    def matches(self, *, package: str, failure_class: str, log: str, failure_classes: set[str] | None = None) -> bool:
        classes = failure_classes if failure_classes is not None else {failure_class}
        if self.package != package or self.error_class not in classes:
            return False
        haystack = log or ""
        return all(needle in haystack for needle in self.error_contains)

    def materialize(self, files: dict[str, str]) -> tuple[Replacement, ...] | None:
        concrete: list[Replacement] = []
        for spec in self.replacements:
            old = spec["old"]
            new = spec["new"]
            paths = _target_paths(spec, files)
            hit = False
            for path in paths:
                if old in files[path]:
                    concrete.append(Replacement(path, old, new))
                    hit = True
            if not hit:
                return None
        if not concrete:
            return None
        return tuple(concrete)


def _target_paths(spec: dict[str, str], files: dict[str, str]) -> list[str]:
    if "path" in spec:
        return [spec["path"]] if spec["path"] in files else []
    glob = spec.get("path_glob", "src/**/*.py")
    return sorted(path for path in files if _glob_match(path, glob))


def _glob_match(path: str, pattern: str) -> bool:
    if pattern == "src/**/*.py":
        return _is_application_source(path, suffixes=(".py",))
    if pattern == "src/**/*.java":
        return _is_application_source(path, suffixes=(".java",))
    return path == pattern


def load_rule_toml(text: str, *, source: str) -> RepairRule:
    data = tomllib.loads(text)
    replacements = tuple(dict(item) for item in data.get("replacements", []))
    for item in replacements:
        if "old" not in item or "new" not in item:
            raise ValueError(f"{source} replacement is missing old/new")
        if "path" not in item and "path_glob" not in item:
            item["path_glob"] = "src/**/*.py"
    contains = data.get("error_contains", [])
    if isinstance(contains, str):
        contains = [contains]
    return RepairRule(
        id=str(data["id"]),
        package=str(data["package"]),
        error_class=str(data["error_class"]),
        error_contains=tuple(str(item) for item in contains),
        replacements=replacements,
        source=source,
    )


def load_rules(directory: Path) -> list[RepairRule]:
    if not directory.exists():
        return []
    rules: list[RepairRule] = []
    for path in sorted(directory.glob("*.toml")):
        rules.append(load_rule_toml(path.read_text(encoding="utf-8"), source=str(path)))
    return rules


def load_skill_rules(directory: Path) -> list[RepairRule]:
    """Rules embedded in SKILL.md fences. Prose-only skills contribute nothing."""

    if not directory.exists():
        return []
    rules: list[RepairRule] = []
    for path in sorted(directory.glob("*/SKILL.md")):
        extracted = extract_skill_fence(path.read_text(encoding="utf-8"))
        if extracted is None:
            continue
        rules.append(load_rule_toml(extracted, source=str(path)))
    return rules


def extract_skill_fences(markdown: str) -> list[str]:
    """Every upgradeproof-repair fence in the document, in order."""

    bodies: list[str] = []
    for part in markdown.split(_FENCE)[1:]:
        body = part.split("```", 1)[0].strip()
        if body:
            bodies.append(body + "\n")
    return bodies


def extract_skill_fence(markdown: str) -> str | None:
    fences = extract_skill_fences(markdown)
    return fences[0] if fences else None


def render_rule_toml(rule: RepairRule) -> str:
    lines = [
        f'id = "{rule.id}"',
        f'package = "{rule.package}"',
        f'error_class = "{rule.error_class}"',
        "error_contains = [" + ", ".join(f'"{item}"' for item in rule.error_contains) + "]",
        "",
    ]
    for spec in rule.replacements:
        lines.append("[[replacements]]")
        if "path" in spec:
            lines.append(f'path = "{spec["path"]}"')
        else:
            lines.append(f'path_glob = "{spec.get("path_glob", "src/**/*.py")}"')
        lines.append('old = """')
        lines.append(spec["old"])
        lines.append('"""')
        lines.append('new = """')
        lines.append(spec["new"])
        lines.append('"""')
        lines.append("")
    return "\n".join(lines)


class PromoteError(ValueError):
    pass


def promote_skill(
    skill_markdown: str,
    destination: Path,
    *,
    accept: bool,
    evidence_verdict: str,
) -> Path:
    """Copy a skill fence into a rule file after an explicit maintainer accept.

    Verification has to have already happened. This function does not re-run
    tests and it will not invent a fence from prose.
    """

    if not accept:
        raise PromoteError("Maintainer acceptance is required. Re-run with accept=True.")
    if evidence_verdict not in {"verified_repair", "verified_bump"}:
        raise PromoteError(
            f"Refusing to promote from verdict {evidence_verdict!r}. "
            "A rule is only promoted from a verified run."
        )
    extracted = extract_skill_fence(skill_markdown)
    if extracted is None:
        raise PromoteError("This skill has no upgradeproof-repair fence to promote.")
    rule = load_rule_toml(extracted, source="skill")
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{rule.id}.toml"
    target.write_text(extracted if extracted.endswith("\n") else extracted + "\n", encoding="utf-8")
    return target
