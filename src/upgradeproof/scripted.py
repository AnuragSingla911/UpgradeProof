"""In-memory session used to test harness transitions without installing packages."""

from __future__ import annotations

from upgradeproof.model import Replacement, RunLog


class ScriptedSession:
    def __init__(
        self,
        files: dict[str, str],
        public: list[RunLog],
        upgrade: list[RunLog],
        oracle: list[RunLog] | None = None,
    ):
        self.files = dict(files)
        self.original_files = dict(files)
        self.base_files: dict[str, str] = {}
        self._public = list(public)
        self._upgrade = list(upgrade)
        self._oracle = list(oracle or [])
        self.events: list[str] = []

    def setup(self) -> RunLog:
        self.events.append("setup")
        return RunLog(True, "setup", command=("setup",))

    def run_public_tests(self) -> RunLog:
        self.events.append("public")
        if not self._public:
            return RunLog(False, "no scripted public result")
        return self._public.pop(0)

    def upgrade_dependency(self) -> RunLog:
        self.events.append("upgrade")
        self.base_files = dict(self.files)
        if not self._upgrade:
            return RunLog(False, "no scripted upgrade result")
        return self._upgrade.pop(0)

    def run_oracle(self) -> RunLog:
        self.events.append("oracle")
        if not self._oracle:
            return RunLog(False, "no scripted oracle result")
        return self._oracle.pop(0)

    def snapshot(self) -> dict[str, str]:
        return dict(self.files)

    def application_files(self) -> dict[str, str]:
        return {path: text for path, text in self.files.items() if path.startswith("src/") and path.endswith(".py")}

    def restore_base(self) -> None:
        if self.base_files:
            self.files = dict(self.base_files)

    def restore_original(self) -> None:
        self.files = dict(self.original_files)

    def apply(self, replacements: tuple[Replacement, ...] | list[Replacement]) -> RunLog:
        for item in replacements:
            text = self.files.get(item.path)
            if text is None or item.old not in text:
                return RunLog(False, f"cannot apply {item.path}")
            self.files[item.path] = text.replace(item.old, item.new, 1)
        return RunLog(True, "applied")

    def diff(self) -> str:
        if self.files == self.original_files:
            return ""
        return "--- scripted diff\n"
