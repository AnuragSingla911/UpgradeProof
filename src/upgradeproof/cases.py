"""Load benchmark case manifests."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Case:
    id: str
    title: str
    package: str
    requirement_name: str
    from_version: str
    to_version: str
    project_dir: Path
    oracle_dir: Path
    root: Path
    expected: dict[str, str]
    install_project: bool
    timeout_seconds: int
    cohort: str
    modes: tuple[str, ...]


@dataclass(frozen=True)
class SuiteEntry:
    case: Case
    cohort: str
    modes: tuple[str, ...]


def load_case(path: Path, *, cohort: str, modes: tuple[str, ...]) -> Case:
    data = tomllib.loads((path / "case.toml").read_text(encoding="utf-8"))
    expected = {str(key): str(value) for key, value in data.get("expected", {}).items()}
    return Case(
        id=str(data["id"]),
        title=str(data["title"]),
        package=str(data["package"]),
        requirement_name=str(data.get("requirement_name", data["package"])),
        from_version=str(data["from_version"]),
        to_version=str(data["to_version"]),
        project_dir=path / "project",
        oracle_dir=path / "oracle",
        root=path,
        expected=expected,
        install_project=bool(data.get("install_project", False)),
        timeout_seconds=int(data.get("timeout_seconds", 180)),
        cohort=cohort,
        modes=modes,
    )


def load_suite(repo_root: Path) -> list[Case]:
    manifest = tomllib.loads((repo_root / "cases" / "suite.toml").read_text(encoding="utf-8"))
    cases: list[Case] = []
    for entry in manifest.get("case", []):
        modes = tuple(str(mode) for mode in entry["modes"])
        cohort = str(entry["cohort"])
        cases.append(load_case(repo_root / "cases" / entry["path"], cohort=cohort, modes=modes))
    return cases
