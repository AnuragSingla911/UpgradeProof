"""Workspace for a JDK release upgrade. Public tests run on the real JDK."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from upgradeproof.checks import parse_requirements, rewrite_equality_pin
from upgradeproof.model import Replacement, RunLog

_SKIP_DIRS = {".venv", "build", "__pycache__", ".git", ".pytest_cache"}


class JavaSession:
    """Copy a Java case and compile it with JDK ``from`` then JDK ``to``.

    ``requirements.txt`` holds ``java==11`` style pins. The upgrade rewrites
    that pin. It does not download a library.
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
        from_version: str,
    ):
        self.project_dir = project_dir.resolve()
        self.oracle_dir = oracle_dir.resolve()
        self.root = work_dir
        self.timeout = timeout
        self.requirement_name = requirement_name
        self.to_version = to_version
        self.from_version = from_version
        self.original_files: dict[str, str] = {}
        self.base_files: dict[str, str] = {}
        self.command_log: list[str] = []

    def setup(self) -> RunLog:
        if self.root.exists():
            shutil.rmtree(self.root)
        shutil.copytree(
            self.project_dir,
            self.root,
            ignore=shutil.ignore_patterns("build", "__pycache__", ".git"),
        )
        self.original_files = self.snapshot()
        missing = [
            version
            for version in (self.from_version, self.to_version)
            if self._jdk_home(version) is None
        ]
        if missing:
            return RunLog(False, "missing JDK " + ", ".join(missing), command=("setup",))
        return RunLog(True, "java workspace ready", command=("setup",))

    def upgrade_dependency(self) -> RunLog:
        requirements = self.root / "requirements.txt"
        text = requirements.read_text(encoding="utf-8")
        try:
            rewritten = rewrite_equality_pin(text, self.requirement_name, self.to_version)
        except ValueError as exc:
            return RunLog(False, str(exc), command=("rewrite-pin",))
        requirements.write_text(rewritten, encoding="utf-8")
        self.base_files = self.snapshot()
        return RunLog(True, f"java pin set to {self.to_version}", command=("rewrite-pin", self.to_version))

    def run_public_tests(self) -> RunLog:
        release = self._release()
        classes = self.root / "build" / "public"
        sources = self._java_files(self.root / "src") + self._java_files(self.root / "tests")
        compiled = self._javac(release, classes, sources)
        if not compiled.ok:
            return compiled
        return self._java(release, classes, "PublicTest", prefix=compiled.output)

    def run_oracle(self) -> RunLog:
        release = self._release()
        classes = self.root / "build" / "oracle"
        sources = self._java_files(self.root / "src") + self._java_files(self.oracle_dir)
        compiled = self._javac(release, classes, sources)
        if not compiled.ok:
            return compiled
        return self._java(release, classes, "OracleTest", prefix=compiled.output)

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
            if path.startswith("src/") and path.endswith(".java")
        }

    def restore_base(self) -> None:
        self._restore(self.base_files)

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

    def diff(self) -> str:
        import difflib

        current = self.snapshot()
        chunks: list[str] = []
        for path in sorted(set(self.original_files) | set(current)):
            old = self.original_files.get(path, "")
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
        return "".join(chunk if chunk.endswith("\n") else chunk + "\n" for chunk in chunks)

    def _release(self) -> str:
        text = (self.root / "requirements.txt").read_text(encoding="utf-8")
        for item in parse_requirements(text):
            if item.get("name") == self.requirement_name and "version" in item:
                return item["version"]
        raise RuntimeError(f"missing {self.requirement_name} pin")

    def _jdk_home(self, version: str) -> Path | None:
        override = os.environ.get(f"UPGRADEPROOF_JDK_{version}")
        candidates = []
        if override:
            candidates.append(Path(override))
        candidates.extend(
            [
                Path(f"/usr/lib/jvm/java-{version}-openjdk-amd64"),
                Path(f"/usr/lib/jvm/java-{version}-openjdk-arm64"),
            ]
        )
        for home in candidates:
            if (home / "bin" / "javac").is_file() and (home / "bin" / "java").is_file():
                return home
        return None

    def _javac(self, release: str, out_dir: Path, sources: list[Path]) -> RunLog:
        home = self._jdk_home(release)
        if home is None:
            return RunLog(False, f"missing JDK {release}")
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)
        command = [
            str(home / "bin" / "javac"),
            "--release",
            release,
            "-d",
            str(out_dir),
            *[str(path) for path in sources],
        ]
        return self._run(command)

    def _java(self, release: str, classes: Path, main: str, *, prefix: str) -> RunLog:
        home = self._jdk_home(release)
        if home is None:
            return RunLog(False, f"missing JDK {release}")
        log = self._run([str(home / "bin" / "java"), "-cp", str(classes), main])
        return RunLog(
            log.ok,
            f"{prefix}\n{log.output}".strip(),
            timed_out=log.timed_out,
            command=log.command,
        )

    def _java_files(self, root: Path) -> list[Path]:
        if not root.exists():
            return []
        return sorted(path for path in root.rglob("*.java") if path.is_file())

    def _iter_files(self):
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            parts = path.relative_to(self.root).parts
            if any(part in _SKIP_DIRS for part in parts):
                continue
            yield path

    def _restore(self, files: dict[str, str]) -> None:
        current = self.snapshot()
        for relative, text in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        for relative in current:
            if relative not in files:
                path = self.root / relative
                if path.is_file() and "build" not in Path(relative).parts:
                    path.unlink()

    def _run(self, command: list[str]) -> RunLog:
        self.command_log.append(" ".join(command))
        try:
            completed = subprocess.run(
                command,
                cwd=self.root,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return RunLog(False, f"TIMEOUT after {self.timeout}s", timed_out=True, command=tuple(command))
        output = f"{completed.stdout}\n{completed.stderr}".strip()
        return RunLog(completed.returncode == 0, output, command=tuple(command))
