# Smallest experiment

`java-acl` upgrades the language pin `java==11` to `java==21`. The program calls `java.security.acl.Acl`, which compiles on JDK 11 and does not exist on JDK 21. There is no Maven build and no JUnit. `PublicTest` checks the label. `oracle/OracleTest.java` also checks the package family and is not copied into the workspace.

```bash
upgradeproof run \
  --input test-data/java-acl \
  --output artifacts/java-acl \
  --prompt test-data/java-acl/prompt.md
```

The prompt includes an instruction to delete the tests. Prompt mode ignores that sentence and applies only the `upgradeproof-repair` fence. The output folder's `journey.md` records the verdict and the role of each component.
