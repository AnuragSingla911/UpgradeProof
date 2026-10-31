"""Deterministic checks: dependency text, failure class, and patch scope."""

from __future__ import annotations

import re
from pathlib import Path

from upgradeproof.model import Replacement

_ASSERT_LINE = re.compile(r"^\s*assert\b")
_SYMBOL = re.compile(r"'([A-Za-z_][A-Za-z0-9_]*)'")


def parse_requirements(text: str) -> list[dict[str, str]]:
    """Parse the subset of requirements.txt this harness rewrites.

    Equality pins become ``{name, version, raw}``. Path and VCS lines are
    returned as ``{raw}`` only. Comments and blank lines are skipped.
    """

    items: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        pinned = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)==(\S+)$", line)
        if pinned:
            items.append({"name": pinned.group(1), "version": pinned.group(2), "raw": line})
        else:
            items.append({"raw": line})
    return items


def rewrite_equality_pin(text: str, name: str, version: str) -> str:
    # Do not let \s eat the newline that terminates the pin line.
    pattern = re.compile(rf"^({re.escape(name)}==)([^\s#]+)[ \t]*$", re.MULTILINE)
    updated, count = pattern.subn(rf"\g<1>{version}", text)
    if count != 1:
        raise ValueError(f"expected exactly one equality pin for {name}, found {count}")
    return updated


def is_constraint_conflict(output: str) -> bool:
    text = output or ""
    strong = ("ResolutionImpossible", "conflicting dependencies", "The conflict is caused by")
    return any(marker in text for marker in strong)


def primary_error_line(output: str) -> str:
    lines = (output or "").splitlines()
    pytest_errors = [line for line in lines if line.startswith("E   ")]
    if pytest_errors:
        return pytest_errors[-1]
    for line in reversed(lines):
        if re.search(r"(Error|Exception)\b", line):
            return line
    return "\n".join(lines[-8:])


def classify_failure(output: str) -> str:
    """Map a command log to a stable failure class.

    Pip resolver errors are detected in the full log. Test failures are
    classified from the last pytest ``E`` line so an earlier import inside
    the traceback does not hide the exception that actually failed.
    """

    text = output or ""
    if is_constraint_conflict(text):
        return "constraint_conflict"
    line = primary_error_line(text)
    if "SyntaxError" in line:
        return "syntax_error"
    if "unexpected keyword argument" in line:
        return "unexpected_keyword"
    if "required positional argument" in line:
        return "missing_argument"
    if "ImportError" in line or "ModuleNotFoundError" in line or "cannot import name" in line:
        return "import_error"
    if "AttributeError" in line:
        return "attribute_error"
    if "KeyError" in line:
        return "key_error"
    if "AssertionError" in line:
        return "assertion_failure"
    if "TypeError" in line:
        return "type_error"
    return "unknown"


def extract_symbols(output: str) -> list[str]:
    line = primary_error_line(output)
    symbols = _SYMBOL.findall(line) or _SYMBOL.findall(output or "")
    return [symbol for symbol in symbols if len(symbol) > 3]


def suspect_source_files(output: str, files: dict[str, str]) -> set[str]:
    """Files a repair may touch: traceback paths plus call sites of the symbol."""

    symbols = extract_symbols(output)
    found: set[str] = set()
    for path, text in files.items():
        if not _is_application_python(path):
            continue
        name = path.rsplit("/", 1)[-1]
        if path in (output or "") or name in (output or ""):
            found.add(path)
        if any(symbol in text for symbol in symbols):
            found.add(path)
    return found


def _is_application_python(path: str) -> bool:
    parts = Path(path).parts
    return (
        path.startswith("src/")
        and path.endswith(".py")
        and ".." not in parts
        and "tests" not in parts
        and "oracle" not in parts
    )


def validate_replacements(
    files: dict[str, str],
    replacements: list[Replacement],
    *,
    trusted: bool,
    suspects: set[str],
    max_files: int = 5,
    max_changed_lines: int = 80,
) -> list[str]:
    """Return reasons to reject a patch. An empty list means the patch may run."""

    reasons: list[str] = []
    if not replacements:
        return ["empty patch"]
    paths = {item.path for item in replacements}
    if len(paths) > max_files:
        reasons.append(f"patch touches {len(paths)} files; limit is {max_files}")

    changed_lines = 0
    for item in replacements:
        path_reasons = _path_reasons(item.path, trusted=trusted, suspects=suspects)
        reasons.extend(path_reasons)
        original = files.get(item.path)
        if original is None:
            reasons.append(f"{item.path} is not an application source file")
            continue
        if item.old == item.new:
            reasons.append(f"{item.path} replacement does not change text")
            continue
        if item.old not in original:
            reasons.append(f"{item.path} does not contain the text to replace")
            continue
        updated = original.replace(item.old, item.new, 1)
        changed_lines += _changed_line_count(original, updated)
        reasons.extend(_assert_reasons(item.old, item.new, item.path))
        files = {**files, item.path: updated}
    if changed_lines > max_changed_lines:
        reasons.append(f"patch changes about {changed_lines} lines; limit is {max_changed_lines}")
    return reasons


def _path_reasons(path: str, *, trusted: bool, suspects: set[str]) -> list[str]:
    reasons: list[str] = []
    parts = Path(path).parts
    if path.startswith("/") or ".." in parts or not path:
        reasons.append(f"unsafe path {path}")
        return reasons
    if "tests" in parts or "oracle" in parts or path.startswith("tests/"):
        reasons.append(f"protected test modification: {path}")
        return reasons
    if path.endswith("requirements.txt") or path.endswith("pyproject.toml"):
        reasons.append(f"dependency metadata is owned by the harness: {path}")
    if not _is_application_python(path):
        reasons.append(f"outside application source: {path}")
    elif not trusted and path not in suspects:
        reasons.append(f"outside failure scope: {path}")
    return reasons


def _assert_reasons(old: str, new: str, path: str) -> list[str]:
    removed = _assert_lines(old) - _assert_lines(new)
    if removed:
        return [f"protected assertion removed in {path}"]
    return []


def _assert_lines(text: str) -> set[str]:
    return {line.strip() for line in text.splitlines() if _ASSERT_LINE.match(line)}


def _changed_line_count(before: str, after: str) -> int:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    if before_lines == after_lines:
        return 0
    # A bound, not a precise diff: enough to reject a file rewrite.
    return max(len(before_lines), len(after_lines))


def validate_diff_text(diff: str) -> list[str]:
    """Reject a unified diff that edits tests or deletes an assertion.

    This is the text-level gate exposed to MCP callers. The investigation
    harness uses ``validate_replacements``, which also checks scope.
    """

    reasons: list[str] = []
    current = ""
    for line in (diff or "").splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            parts = Path(current).parts
            if "tests" in parts or "oracle" in parts or current.startswith("tests/"):
                reasons.append(f"protected test modification: {current}")
        if line.startswith("-") and not line.startswith("---") and _ASSERT_LINE.match(line[1:]):
            reasons.append(f"protected assertion removed in {current or 'diff'}")
    return reasons


def resolve_inside(root: Path, relative: str) -> Path:
    """Resolve ``relative`` and require it to stay inside ``root``."""

    if not relative or relative.startswith("/"):
        raise PermissionError(f"path escapes the workspace: {relative}")
    candidate = (root / relative).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise PermissionError(f"path escapes the workspace: {relative}")
    return candidate
