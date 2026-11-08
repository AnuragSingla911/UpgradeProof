# Upgrade investigation procedure

The harness runs this procedure. A prompt does not get to mark a run successful.

## Bounds

- One pin, Java 11 to Java 17.
- At most two repair attempts.
- The prompt's `upgradeproof-repair` fence is the only executable repair. Other sentences are ignored.
- A run stops at its timeout.

## States

1. **setup.** Copy the application. Do not copy a hidden oracle into that workspace.
2. **baseline.** Compile and run the public tests on JDK 11. If they fail, stop with `invalid_baseline`.
3. **upgrade.** Rewrite the single `java==11` pin to `java==17`.
4. **retest.** Run the public tests on JDK 17. If they pass, the verdict is `verified_bump`.
5. **classify.** A missing JDK package or symbol is `missing_symbol`.
6. **propose.** Apply every repair fence whose error class appears in the compiler log and whose old source text is present. Fences come from the prompt and from `skills/`. One fence covers one error class. A diagnostic with no fence ends the run as `unresolved` and names that class.
7. **reject or apply.** Reject a patch that edits tests or leaves `src/`.
8. **retest the repair.** Run the public tests again.
9. **oracle.** Run hidden checks only when the case has them and the public tests passed. A repository's own tests are enough when it has no oracle.
10. **stop.** `verified_repair` keeps the patched tree and writes it to `java-17/`. Any other verdict restores the unpatched tree and delivers no patch.

Passing tests are evidence only for the behaviors those tests execute. They do not prove the project is compatible with JDK 17 in every environment.
