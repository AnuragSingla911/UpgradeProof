# JDK 11 passes, JDK 17 fails

`java.security.acl.Acl` compiles on JDK 11 and was removed in JDK 17. There is no Maven build and no JUnit.

| Folder | Pin | What the public test does |
|---|---|---|
| `java-11/` | `java==11` | Compiles and prints `public ok` |
| `java-17/` | `java==17` | Same source and the same test. `javac` reports that `java.security.acl` does not exist |

`java-17/` is that broken upgrade before any repair. It is not a second harness input. The harness starts from `java-11/`, rewrites the pin to 17, and applies only the fence in `prompt.md`. The sentence that says to delete the tests is ignored. `oracle/OracleTest.java` also checks the package family and is not copied into the workspace.

```bash
export UPGRADEPROOF_JDK_11="$(brew --prefix openjdk@11)"
export UPGRADEPROOF_JDK_17="$(brew --prefix openjdk@17)"

upgradeproof run \
  --input test-data \
  --output artifacts/java-11-to-17 \
  --prompt test-data/prompt.md
```

On Linux the session also finds `/usr/lib/jvm/java-11-openjdk-*` and `/usr/lib/jvm/java-17-openjdk-*`. A good run exits 0 with verdict `verified_repair`. The patch changes `java==11` to `java==17` and does not edit `tests/`.
