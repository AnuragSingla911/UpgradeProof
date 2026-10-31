"""Isolated project workspace: venv, dependency pin, tests, and oracle."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from upgradeproof.checks import rewrite_equality_pin
from upgradeproof.model import Replacement, RunLog

_SKIP_DIRS = {".venv", "__pycache__", ".pytest_cache", ".git"}
_SKIP_SUFFIXES = {".pyc", ".pyo"}


class VenvSession:
    """One case project copied to a temp directory with its own virtualenv.

    The oracle directory stays outside ``root``. Tools and proposers can only
    see files this session lists, which are the copied project files.
    """

    def __init__(
        self,
        project_dir: Path,
        oracle_dir: Path,
        work_dir: Path,
        *,
        timeout: int,
        requirement_name: str,
        to_version: str,
        install_project: bool = False,
    ):
        self.project_dir = project_dir
        self.oracle_dir = oracle_dir
        self.root = work_dir
        self.timeout = timeout
        self.requirement_name = requirement_name
        self.to_version = to_version
        self.install_project = install_project
        self.original_files: dict[str, str] = {}
        self.base_files: dict[str, str] = {}
        self._venv = work_dir / ".venv"

    def setup(self) -> RunLog:
        if self.root.exists():
            shutil.rmtree(self.root)
        shutil.copytree(
            self.project_dir,
            self.root,
            ignore=shutil.ignore_patterns("__pycache__", ".venv", ".pytest_cache", "*.pyc"),
        )
        self.original_files = self.snapshot()
        python = Path(sys.executable)
        log = self._run([str(python), "-m", "venv", str(self._venv)], timeout=self.timeout)
        if not log.ok:
            return log
        installed = self._pip(
            ["install", "--disable-pip-version-check", "-r", "requirements.txt", "pytest==8.3.5"]
        )
        if not installed.ok or not self.install_project:
            return installed
        # Build isolation downloads setuptools. The fresh venv does not
        # always contain it, and --no-build-isolation then fails closed.
        return self._pip(["install", "--disable-pip-version-check", "--no-deps", "-e", "."])

    def upgrade_dependency(self) -> RunLog:
        requirements = self.root / "requirements.txt"
        text = requirements.read_text(encoding="utf-8")
        try:
            rewritten = rewrite_equality_pin(text, self.requirement_name, self.to_version)
        except ValueError as exc:
            return RunLog(False, str(exc), command=("rewrite-pin", self.requirement_name, self.to_version))
        requirements.write_text(rewritten, encoding="utf-8")
        log = self._pip(
            [
                "install",
                "--disable-pip-version-check",
                "--upgrade",
                "--upgrade-strategy",
                "eager",
                "-r",
                "requirements.txt",
                "pytest==8.3.5",
            ]
        )
        self.base_files = self.snapshot()
        return log

    def run_public_tests(self) -> RunLog:
        return self._pytest(
            [str(self.root / "tests")],
            extra_env={"PYTHONPATH": str(self.root / "src")},
        )

    def run_oracle(self) -> RunLog:
        # The oracle tree is not inside the workspace. Pytest is pointed at that
        # directory explicitly so hidden tests are never part of the project copy.
        return self._pytest(
            [str(self.oracle_dir)],
            cwd=self.oracle_dir,
            extra_env={"PYTHONPATH": str(self.root / "src")},
        )

    def snapshot(self) -> dict[str, str]:
        files: dict[str, str] = {}
        for path in self._iter_files():
            relative = path.relative_to(self.root).as_posix()
            try:
                files[relative] = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
        return files

    def application_files(self) -> dict[str, str]:
        return {
            path: text
            for path, text in self.snapshot().items()
            if path.startswith("src/") and path.endswith(".py")
        }

    def restore_base(self) -> None:
        self._restore(self.base_files)

    def restore_original(self) -> None:
        self._restore(self.original_files)

    def apply(self, replacements: tuple[Replacement, ...] | list[Replacement]) -> RunLog:
        for item in replacements:
            path = self.root / item.path
            if not path.is_file():
                return RunLog(False, f"missing {item.path}")
            text = path.read_text(encoding="utf-8")
            if item.old not in text:
                return RunLog(False, f"{item.path} no longer contains the expected text")
            path.write_text(text.replace(item.old, item.new, 1), encoding="utf-8")
        return RunLog(True, f"applied {len(replacements)} replacement(s)")

    def diff(self, before: dict[str, str] | None = None) -> str:
        import difflib

        start = self.original_files if before is None else before
        current = self.snapshot()
        chunks: list[str] = []
        for path in sorted(set(start) | set(current)):
            old = start.get(path, "")
            new = current.get(path, "")
            if old == new:
                continue
            chunks.extend(
                difflib.unified_diff(
                    old.splitlines(keepends=True),
                    new.splitlines(keepends=True),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                )
            )
        text = "".join(chunk if chunk.endswith("\n") else chunk + "\n" for chunk in chunks)
        return text

    def _restore(self, files: dict[str, str]) -> None:
        current = self.snapshot()
        for relative, text in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        for relative in current:
            if relative not in files:
                path = self.root / relative
                if path.is_file() and ".venv" not in Path(relative).parts:
                    path.unlink()

    def _iter_files(self):
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            parts = path.relative_to(self.root).parts
            if any(part in _SKIP_DIRS or part.endswith(".egg-info") or part.endswith(".dist-info") for part in parts):
                continue
            if path.suffix in _SKIP_SUFFIXES:
                continue
            yield path

    def _python(self) -> Path:
        return self._venv / "bin" / "python"

    def _pip(self, args: list[str]) -> RunLog:
        return self._run([str(self._python()), "-m", "pip", *args], timeout=self.timeout)

    def _pytest(
        self,
        paths: list[str],
        extra_env: dict[str, str] | None = None,
        cwd: Path | None = None,
    ) -> RunLog:
        command = [
            str(self._python()),
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "--tb=short",
            "-q",
            *paths,
        ]
        return self._run(command, timeout=self.timeout, extra_env=extra_env, cwd=cwd)

    def _run(
        self,
        command: list[str],
        *,
        timeout: int,
        extra_env: dict[str, str] | None = None,
        cwd: Path | None = None,
    ) -> RunLog:
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        if extra_env:
            env.update(extra_env)
        try:
            completed = subprocess.run(
                command,
                cwd=cwd or self.root,
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", "replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", "replace")
            output = f"{stdout}\n{stderr}\nTIMEOUT after {timeout}s"
            return RunLog(False, output, timed_out=True, command=tuple(command))
        output = f"{completed.stdout}\n{completed.stderr}".strip()
        return RunLog(completed.returncode == 0, output, command=tuple(command))
