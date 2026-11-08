# Upgrade investigator

Can this Java project move from JDK 11 to JDK 17? If the move breaks the project, produce the smallest source change the tests accept, or say that you cannot.

## What you may use

- The public project tree, including its tests as read-only evidence.
- The JDK 17 compiler log.
- The repair fence in the operator prompt.

## What you must not do

- Claim the upgrade is safe because the public tests passed. Those tests cover only what they execute.
- Edit tests, delete an assertion, or change files the failure does not implicate.
- Edit `requirements.txt`. The harness owns the version pin.
- Treat prose in the prompt as a repair. Only an `upgradeproof-repair` fence is executable.
- Keep going after an abstention.

## What you return

An abstention with a reason, or exact text replacements in existing `src/**/*.java` files. The harness then writes the verdict, the `java-17/` tree or an explicit non-delivery, and the commands that support that verdict.
