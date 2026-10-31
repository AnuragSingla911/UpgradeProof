# UpgradeProof

UpgradeProof takes a public GitHub repository that contains a Java 11 app and asks one question: can that app move to JDK 17? If the move breaks the tests, it applies the repair fence in the prompt, reruns the tests, and writes the repaired tree to `java-17/` in that same repository.

The harness sets the verdict. The prompt states the upgrade. Each known break is a separate fence in [`skills/jdk/SKILL.md`](skills/jdk/SKILL.md), and each fence names the error class it covers. A compiler error with no fence stays unresolved.

The two contracts are [`workflow.md`](workflow.md) and [`agent.md`](agent.md). The known repair lives in [`skills/jdk/SKILL.md`](skills/jdk/SKILL.md).

## Chat

JDK 11 and JDK 17 must be installed. On a Mac, point the session at Homebrew:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
export UPGRADEPROOF_JDK_11="$(brew --prefix openjdk@11)"
export UPGRADEPROOF_JDK_17="$(brew --prefix openjdk@17)"
upgradeproof chat
```

Open http://127.0.0.1:8765. The page is filled with the sample repository and the prompt. A verified run pushes `java-17/` and `journey.md` to that repository.

Sample: [Java11to17UpgradeSample](https://github.com/AnuragSingla911/Java11to17UpgradeSample)

## Local case

`test-data/java-11` passes on JDK 11. `test-data/java-17` is the same source with the pin moved to 17, where compilation fails. The harness starts from `java-11` and does not read the `java-17` snapshot.

```bash
upgradeproof run \
  --input test-data \
  --output artifacts/java-11-to-17 \
  --prompt test-data/prompt.md
```

Passing tests are evidence only for the behaviors those tests execute.
