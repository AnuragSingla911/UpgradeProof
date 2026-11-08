# UpgradeProof

[UpgradeProof](https://github.com/AnuragSingla911/UpgradeProof) is a small harness that answers one question for a **Java 11** application: can it move to **JDK 17** with evidence?

It clones or loads the app, runs public tests on JDK 11, bumps the `java==11` pin to `java==17`, classifies compiler failures, applies trusted repair fences from **skills** (and optionally from the prompt), reruns tests and optional hidden oracles, and writes **`java-17/`**, **`journey.md`**, and **`evidence.md`** when the verdict is verified.

The **harness** sets the verdict. The **prompt** states the upgrade goal. Each known break is a separate `upgradeproof-repair` fence in [`skills/jdk/SKILL.md`](skills/jdk/SKILL.md), tagged with an **error class**. A failure with no matching fence stays **`unresolved`**.

| Doc | Role |
| --- | --- |
| [`workflow.md`](workflow.md) | Procedure the harness runs (baseline → upgrade → classify → propose → oracle) |
| [`agent.md`](agent.md) | What an investigator may change and what it must not do |
| [`skills/jdk/SKILL.md`](skills/jdk/SKILL.md) | JDK skill: one fence per known break (today: `missing_symbol` for removed `java.security.acl`) |

**Sample target repository:** [Java11to17UpgradeSample](https://github.com/AnuragSingla911/Java11to17UpgradeSample) — layout `java-11/` (passing on 11), optional `java-17/` after a verified run.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/upgradeproof/` | Harness, JDK session, GitHub clone/push, local chat server |
| `skills/` | Package skills (`jdk/SKILL.md`, …) loaded by `PromptProposer` |
| `test-data/` | Local JDK 11→17 case (`java-11/`, oracle, `prompt.md`, `case.toml`) |
| `web/index.html` | Chat UI served by `upgradeproof chat` |
| `cases/`, `docs/`, `rules/` | Earlier Python dependency benchmark artifacts (not used by the Java CLI path) |

**CI:** [`.github/workflows/test.yml`](.github/workflows/test.yml) installs JDK 11 and 17 on Ubuntu and runs `pytest`.

## Requirements

- **Python** ≥ 3.11 (3.12 recommended)
- **JDK 11** and **JDK 17** on the machine running the harness

On macOS (Homebrew):

```bash
brew install openjdk@11 openjdk@17
```

On Ubuntu (as in CI): `openjdk-11-jdk-headless`, `openjdk-17-jdk-headless`.

## Install

```bash
git clone https://github.com/AnuragSingla911/UpgradeProof.git
cd UpgradeProof
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### Environment variables

| Variable | Purpose |
| --- | --- |
| `UPGRADEPROOF_JDK_11` | JDK 11 home (directory containing `bin/javac`) |
| `UPGRADEPROOF_JDK_17` | JDK 17 home |
| `UPGRADEPROOF_SKILLS` | Optional path to this repo’s `skills/` when the harness runs from a temp clone (chat/GitHub flow resolves skills from the installed package by default) |

Example (macOS):

```bash
export UPGRADEPROOF_JDK_11="$(brew --prefix openjdk@11)"
export UPGRADEPROOF_JDK_17="$(brew --prefix openjdk@17)"
```

`upgradeproof chat` also probes common Homebrew paths if these are unset.

## Commands

### `upgradeproof chat` — GitHub URL in the browser

Starts a local server (default **http://127.0.0.1:8765**) with a form: public GitHub URL + upgrade prompt. **POST `/api/upgrade`** clones the repo, runs the harness, and (on a verified repair) can commit and push `java-17/`, `journey.md`, and `evidence.md`.

```bash
upgradeproof chat
# custom bind: upgradeproof chat --host 127.0.0.1 --port 9000
```

Open the URL printed in the terminal so the page calls the same-origin API. If you open `web/index.html` as `file://`, the script falls back to `http://127.0.0.1:8765` (default chat port). Use `--port` when **8765** is already taken.

**Push** needs `git` credentials for the target repo (HTTPS token or SSH). Failures appear as `publish_error` in the JSON response; the local upgrade can still succeed with `pushed: false`.

**Expected repository shape:**

- `java-11/requirements.txt` with `java==11` and `java-11/src/`, `java-11/tests/`, or the same layout at repo root.

Default form fields use [Java11to17UpgradeSample](https://github.com/AnuragSingla911/Java11to17UpgradeSample) and [`test-data/chat-prompt.md`](test-data/chat-prompt.md).

### `upgradeproof run` — local folder

Runs one case from a directory containing `case.toml` and `java-11/` (see [`test-data/`](test-data/README.md)).

```bash
upgradeproof run \
  --input test-data \
  --output artifacts/java-11-to-17 \
  --prompt test-data/prompt.md
```

Writes `evidence.md`, `journey.md`, `patch.diff`, and `result.json` under `--output`. Exit code **0** when the verdict is `verified_repair` or `verified_bump`.

## Verdicts (summary)

- **`verified_bump`** — public tests pass after the pin change alone.
- **`verified_repair`** — tests pass after applying a trusted fence (skill or prompt).
- **`unresolved`** — timeout, no fence for the failure class, patch rejected, tests still failing, etc.
- **`invalid_baseline`** — `java-11` public tests fail before upgrade.
- **`constraint_conflict`** — reserved for dependency resolver conflicts (Python bench); not used for the Java pin flow.

Details: [`workflow.md`](workflow.md).

## Tests

```bash
pytest
```

[`tests/test_java_prompt.py`](tests/test_java_prompt.py) covers URL parsing, skills resolution when `cwd` is not the repo, failure classes, proposer behavior, `run`, and `upgrade_checkout` when JDKs are available.

## License

MIT — see [`LICENSE`](LICENSE).
