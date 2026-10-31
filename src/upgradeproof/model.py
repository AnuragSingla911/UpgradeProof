"""Shared records for an upgrade investigation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Replacement:
    path: str
    old: str
    new: str


@dataclass(frozen=True)
class Proposal:
    """A candidate repair.

    ``trusted`` is reserved for maintainer-authored rules and skill fences.
    Model output is untrusted and must pass scope checks before it is applied.
    """

    source: str
    replacements: tuple[Replacement, ...] = ()
    rationale: str = ""
    abstain: bool = False
    abstain_reason: str = ""
    counts_as_model_call: bool = False
    trusted: bool = False

    @staticmethod
    def abstention(source: str, reason: str, *, model_call: bool = False) -> Proposal:
        return Proposal(
            source=source,
            abstain=True,
            abstain_reason=reason,
            counts_as_model_call=model_call,
        )


@dataclass
class RunLog:
    ok: bool
    output: str
    timed_out: bool = False
    command: tuple[str, ...] = ()

    def tail(self, limit: int = 4000) -> str:
        text = self.output or ""
        if len(text) <= limit:
            return text
        return text[-limit:]


@dataclass
class ProposalRequest:
    case_id: str
    package: str
    from_version: str
    to_version: str
    failure_class: str
    log: str
    files: dict[str, str]
    feedback: str = ""
    attempt: int = 1


@dataclass
class Evidence:
    case_id: str
    title: str
    mode: str
    verdict: str
    reason: str
    failure_class: str | None = None
    repair_source: str | None = None
    attempts: int = 0
    model_calls: int = 0
    wall_clock_seconds: float = 0.0
    setup_seconds: float = 0.0
    estimated_cost_usd: float = 0.0
    patch: str = ""
    rejections: list[str] = field(default_factory=list)
    baseline_passed: bool | None = None
    upgrade_passed: bool | None = None
    public_tests_passed: bool | None = None
    oracle_passed: bool | None = None
    timeline: list[dict[str, object]] = field(default_factory=list)
    limitation: str = ""
    expected_verdict: str | None = None
    expectation_met: bool | None = None

    @property
    def verified(self) -> bool:
        return self.verdict in {"verified_repair", "verified_bump"}
