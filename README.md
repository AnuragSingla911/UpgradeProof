# UpgradeProof

UpgradeProof asks one question of a small Python project:

**Can this project upgrade dependency X from version A to version B? If that breaks the tests, what is the smallest change that still behaves the way the tests require?**

It is a feasibility bench for harness engineering, not a general dependency bot. The interesting part is not opening a version-bump pull request. It is the line between a one-off repair and a repair that has become a checked, reusable rule.

## What a run does

1. Run the project's public tests on the pinned dependency.
2. Change only that pin and reinstall.
3. Classify a failure with deterministic checks.
4. Apply a promoted rule or a skill fence when its preconditions hold. Otherwise abstain. A model is used only if you explicitly select `cpu` or `hosted`.
5. Reject patches that edit tests, delete assertions, or wander outside the failure.
6. Re-run the public tests, then hidden oracle tests that the repair step cannot read.
7. Write a patch and an evidence report, or an explicit unresolved result.

Passing tests are evidence for the behaviors those tests execute. They are not proof of universal compatibility.

## Why these cases

The fixtures are small programs written for this repository. Each one pins a real package, upgrades it, and breaks on a documented change:

| Case | Upgrade | Break |
|---|---|---|
| `urllib3-retry` | 1.26.20 → 2.2.3 | `Retry(method_whitelist=...)` was removed |
| `werkzeug-url-quote` | 2.3.8 → 3.0.6 | `werkzeug.urls.url_quote` was removed |
| `importlib-entry-points` | 4.13.0 → 8.5.0 | `entry_points()[group]` no longer selects a group |
| `itsdangerous-serializer` | 1.1.0 → 2.2.0 | `TimedJSONWebSignatureSerializer` was removed |
| `packaging-legacy-version` | 21.3 → 24.2 | `LegacyVersion` was removed |

A sixth package, MarkupSafe `soft_unicode`, is an **uncovered** probe: the skill is prose only, so both modes must abstain. Adversarial cases cover an already-failing baseline, a clean version bump, and a dependency conflict. Guard checks cover a deleted assertion, a test edit, an unrelated edit, an invented API, an oracle miss, a retry limit, and abstention.

The promoted rules were written with these fixtures. Treat the verified rate as evidence that the harness can reuse a checked repair, not as a prediction about other repositories. Newly authored cases avoid presenting the bench as free of training-data contamination; they do not make it contamination-free if a model has seen the upstream changelogs.

## Harness map

| Piece | Responsibility |
|---|---|
| [`workflow.md`](workflow.md) | Investigation procedure, bounds, and stop conditions |
| [`agent.md`](agent.md) | Investigator role and evidence requirement |
| [`skills/`](skills/) | Migration knowledge. Only an `upgradeproof-repair` fence is executable |
| [`rules.md`](rules.md) | Allowed edits and what a reviewer should believe |
| [`rules/promoted/`](rules/promoted/) | Fences accepted for reuse with no model |
| `src/upgradeproof/checks.py` | Pin parsing, failure classes, diff rejection |
| `src/upgradeproof/harness.py` | State machine, attempts, timeouts, verdicts |
| `src/upgradeproof/mcp_server.py` | The same operations behind a small MCP tool list |
| `src/upgradeproof/benchmark.py` | Verified repairs, abstentions, time, model calls, cost |

Rules mode and skill mode are both zero-cost. They exist so a reader can see the same repair as a document and as a promoted rule. Promotion is `upgradeproof promote <skill> --verdict verified_repair --rules-dir ... --accept`. Without `--accept`, or without a verified verdict, nothing is written.

## Modes and cost

| Mode | What runs | Spend |
|---|---|---|
| `rules` (default) | Promoted rules | None |
| `skill` | Skill fences only. Prose is ignored | None |
| `cpu` | A local GGUF via `llama-cpp-python`, if `UPGRADEPROOF_GGUF` points at a file | None, and it can fail |
| `hosted` | An OpenAI-compatible chat endpoint | Only when base URL, API key, and model are all set. No automatic fallback |

GitHub Models, including its inference API, has been retired, so this project does not depend on it. See [GitHub Models](https://docs.github.com/en/github-models).

Hosted cost is `model_calls * UPGRADEPROOF_PRICE_PER_CALL` when that variable is a number you set. The bench does not invent a price.

CPU inference is optional because a small model may not emit a valid repair. The default bench records the CPU arm as not run until you pass `--cpu` with a model file. Start there before describing CPU inference as a useful free repair experience.

## Run

```bash
python -m pip install -e ".[dev]"
pytest
upgradeproof benchmark --out docs
```

One Python case:

```bash
upgradeproof investigate cases/urllib3_retry --mode rules --out artifacts
```

Smallest Java experiment. JDK 11 and JDK 21 must both be installed (`openjdk-11-jdk-headless` and `openjdk-21-jdk-headless`, or `UPGRADEPROOF_JDK_11` / `UPGRADEPROOF_JDK_21`). The prompt's fence is the only executable part of the prompt. The command writes `evidence.md`, `journey.md`, `patch.diff`, and `result.json` into the output folder:

```bash
upgradeproof run \
  --input test-data/java-acl \
  --output artifacts/java-acl \
  --prompt test-data/java-acl/prompt.md
```

MCP, rooted at the current directory, with PyPI lookup off:

```bash
upgradeproof mcp
```

The tools are `list_dependencies`, `classify_failure`, `validate_diff`, `read_file`, `search_code`, `package_metadata`, and `run_tests`. `run_tests` always runs `tests/` inside the workspace. Paths that leave the workspace are refused. That check is not an operating-system sandbox. The GitHub Actions job that runs this suite requests `contents: read` so it can check out the repo and `actions: write` so it can upload the results artifact. It has no secret and it does not push.

[GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions): standard hosted runners are free for public repositories; larger runners are billed. This workflow uses `ubuntu-latest` and keeps the artifact to the JSON, the summary, and the evidence files.

GitHub Pages can serve `docs/` as a static dashboard. The page reads `docs/results.js` produced by the benchmark. It does not run investigations. See [About GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages).

## Results

The numbers below are filled in from `docs/results.json` after a local bench run. Row times include environment setup and are not additive across modes. `elapsed_seconds` is the real stopwatch.

<!-- RESULTS -->
Local bench on 31 Oct 2026, 1:42pm Asia/Calcutta, Python 3.12, elapsed **54.4s**. Every expectation in the suite was met. No delivered patch failed its oracle (`0` regressions). Model calls on the rules and skill arms were `0`, and estimated cost was `$0`.

| Cohort | Expectations | Verified verdicts | Model calls | Cost per verified repair |
|---|---:|---:|---:|---:|
| Repair, rules | 5/5 | 5/5 | 0 | $0 |
| Repair, skill fences | 5/5 | 5/5 | 0 | $0 |
| Uncovered MarkupSafe | 1/1 abstained | 0/1 | 0 | n/a |
| Adversarial baselines | 3/3 | 1/3 (the clean bump only) | 0 | $0 |

The uncovered case is supposed to stay unresolved: its skill has no executable fence. The adversarial cases are supposed to report `invalid_baseline`, `verified_bump`, and `constraint_conflict`. Two execution probes on real installs also held: an invented urllib3 keyword failed the public tests and was not delivered, and a packaging edit that passed the public test but dropped legacy-version behavior failed the oracle and was not delivered.

Promotion, on the second urllib3 fixture: a scripted first-encounter proposal (not a neural model) verified in one model call, the skill fence was accepted, and the restored project was then repaired by that promoted rule with **zero** model calls.

The CPU arm did not run. `llama-cpp-python` has no prebuilt wheel for this interpreter, so the bench records `unavailable` instead of a made-up score. Set `UPGRADEPROOF_GGUF` and install the `cpu` extra before treating a small model as a repair engine.
<!-- /RESULTS -->
