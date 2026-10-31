"""Repair proposers. Rules and skills do not call a model."""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

from upgradeproof.knowledge import RepairRule, load_rules, load_skill_rules
from upgradeproof.model import Proposal, ProposalRequest, Replacement

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


class RulesProposer:
    def __init__(self, rules: list[RepairRule]):
        self.rules = rules

    @classmethod
    def from_directory(cls, directory: Path) -> RulesProposer:
        return cls(load_rules(directory))

    def propose(self, request: ProposalRequest) -> Proposal:
        return _propose_from_rules(self.rules, request, source_prefix="rule")


class SkillProposer:
    """Execute only machine-readable skill fences. Prose is not a repair."""

    def __init__(self, rules: list[RepairRule]):
        self.rules = rules

    @classmethod
    def from_directory(cls, directory: Path) -> SkillProposer:
        return cls(load_skill_rules(directory))

    def propose(self, request: ProposalRequest) -> Proposal:
        return _propose_from_rules(self.rules, request, source_prefix="skill")


class FixedProposer:
    """Evaluation double. Not an inference backend."""

    def __init__(
        self,
        proposal: Proposal,
        *,
        script: list[Proposal] | None = None,
    ):
        self.proposal = proposal
        self.script = list(script or [])

    def propose(self, request: ProposalRequest) -> Proposal:
        del request
        if self.script:
            return self.script.pop(0)
        return self.proposal


class HostedProposer:
    """Optional paid model. There is no fallback to another backend.

    The process must be started in hosted mode with all three settings:
    ``UPGRADEPROOF_API_BASE``, ``UPGRADEPROOF_API_KEY``, and
    ``UPGRADEPROOF_MODEL``.
    """

    def __init__(self, environ: dict[str, str] | None = None, opener=None):
        env = os.environ if environ is None else environ
        self.base = (env.get("UPGRADEPROOF_API_BASE") or "").rstrip("/")
        self.api_key = env.get("UPGRADEPROOF_API_KEY") or ""
        self.model = env.get("UPGRADEPROOF_MODEL") or ""
        self.opener = opener or urllib.request.urlopen
        self.price_per_call = _price(env.get("UPGRADEPROOF_PRICE_PER_CALL"))

    def missing_settings(self) -> list[str]:
        missing = []
        if not self.base:
            missing.append("UPGRADEPROOF_API_BASE")
        if not self.api_key:
            missing.append("UPGRADEPROOF_API_KEY")
        if not self.model:
            missing.append("UPGRADEPROOF_MODEL")
        return missing

    def propose(self, request: ProposalRequest) -> Proposal:
        missing = self.missing_settings()
        if missing:
            return Proposal.abstention(
                "model:hosted",
                "hosted_not_configured: " + ", ".join(missing),
                model_call=False,
            )
        prompt = _repair_prompt(request)
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 512,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You propose the smallest source repair for one dependency "
                        "upgrade. Reply with one JSON object and no other text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        raw = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            self.base + "/chat/completions",
            data=raw,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self.opener(http_request, timeout=60) as response:
                body = response.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001 - the harness must record the failure, not switch modes
            return Proposal.abstention("model:hosted", f"hosted_call_failed: {exc}", model_call=True)
        try:
            content = json.loads(body)["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
            return Proposal.abstention("model:hosted", f"hosted_bad_response: {exc}", model_call=True)
        return _proposal_from_model_text(content, source="model:hosted")


class CpuProposer:
    """Small local GGUF model, loaded only when a file and llama-cpp are present.

    The model is asked to choose a bounded JSON repair. It is not used unless
    the investigation mode is ``cpu``.
    """

    def __init__(self, model_path: Path | None):
        self.model_path = model_path
        self._llm = None
        self._import_error = ""

    def status(self) -> str:
        if self.model_path is None or not self.model_path.is_file():
            return "unavailable: set UPGRADEPROOF_GGUF to a local GGUF file"
        try:
            import llama_cpp  # noqa: F401
        except ImportError:
            return "unavailable: install the cpu extra (llama-cpp-python)"
        return "ready"

    def propose(self, request: ProposalRequest) -> Proposal:
        status = self.status()
        if status != "ready":
            return Proposal.abstention("model:cpu", status, model_call=False)
        llm = self._load()
        prompt = _repair_prompt(request)
        try:
            result = llm.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "Reply with one JSON object and no other text.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=256,
            )
            content = result["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            return Proposal.abstention("model:cpu", f"cpu_call_failed: {exc}", model_call=True)
        return _proposal_from_model_text(content or "", source="model:cpu")

    def _load(self):
        if self._llm is None:
            from llama_cpp import Llama

            assert self.model_path is not None
            self._llm = Llama(
                model_path=str(self.model_path),
                n_ctx=2048,
                n_threads=os.cpu_count() or 2,
                verbose=False,
            )
        return self._llm


def _propose_from_rules(rules: list[RepairRule], request: ProposalRequest, *, source_prefix: str) -> Proposal:
    log = request.log if not request.feedback else f"{request.log}\n{request.feedback}"
    candidates = [
        rule
        for rule in rules
        if rule.matches(package=request.package, failure_class=request.failure_class, log=log)
    ]
    for rule in candidates:
        materialized = rule.materialize(request.files)
        if materialized:
            return Proposal(
                source=f"{source_prefix}:{rule.id}",
                replacements=materialized,
                rationale=f"Preconditions matched {rule.id}.",
                trusted=True,
            )
    if candidates:
        return Proposal.abstention(source_prefix, "rule preconditions matched but the source text did not")
    return Proposal.abstention(source_prefix, "no promoted repair matches this failure")


def _repair_prompt(request: ProposalRequest) -> str:
    files = []
    for path, text in sorted(request.files.items()):
        snippet = text if len(text) <= 2000 else text[:2000] + "\n# ...truncated...\n"
        files.append(f"### {path}\n{snippet}")
    log = request.log[-2500:]
    feedback = request.feedback[-1000:] if request.feedback else ""
    return (
        f"Package {request.package} changed from {request.from_version} to {request.to_version}.\n"
        f"Failure class: {request.failure_class}\n"
        f"Attempt: {request.attempt}\n\n"
        f"Error log:\n{log}\n\n"
        f"Feedback:\n{feedback}\n\n"
        "Application files:\n"
        + "\n".join(files)
        + "\n\nReturn JSON of the form "
        '{"abstain": false, "rationale": "...", "replacements": '
        '[{"path": "src/pkg/mod.py", "old": "exact text", "new": "exact text"}]}. '
        "Use abstain true if you cannot justify a small repair. "
        "Do not modify tests.\n"
    )


def _proposal_from_model_text(content: str, *, source: str) -> Proposal:
    match = _JSON_OBJECT.search(content or "")
    if not match:
        return Proposal.abstention(source, "model response was not JSON", model_call=True)
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return Proposal.abstention(source, "model response was not JSON", model_call=True)
    if data.get("abstain"):
        return Proposal.abstention(
            source,
            str(data.get("rationale") or "model abstained"),
            model_call=True,
        )
    replacements = []
    for item in data.get("replacements") or []:
        try:
            replacements.append(Replacement(str(item["path"]), str(item["old"]), str(item["new"])))
        except (KeyError, TypeError):
            return Proposal.abstention(source, "model JSON replacements were incomplete", model_call=True)
    if not replacements:
        return Proposal.abstention(source, "model returned no replacements", model_call=True)
    return Proposal(
        source=source,
        replacements=tuple(replacements),
        rationale=str(data.get("rationale") or ""),
        counts_as_model_call=True,
        trusted=False,
    )


def _price(raw: str | None) -> float:
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0
