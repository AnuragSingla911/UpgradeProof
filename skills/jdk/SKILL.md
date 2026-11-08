# JDK 17

A Java 11 to 17 upgrade can fail in many ways. This skill stores one fence per known break. The fence names its error class. A compiler diagnostic with no fence is left unresolved.

Recognized classes include `missing_symbol`, `incompatible_types`, `incompatible_signature`, `inaccessible`, `exception_check`, `ambiguous`, and `syntax_error`.

`java.security.acl` compiles on JDK 11 and was removed in JDK 17. That break is the fence below. Prose in this file is not a repair.

```upgradeproof-repair
id = "jdk-acl-removed"
package = "jdk"
error_class = "missing_symbol"
error_contains = ["java.security.acl"]

[[replacements]]
path_glob = "src/**/*.java"
old = '''        return java.security.acl.Acl.class.getSimpleName();'''
new = '''        return "Acl";'''

[[replacements]]
path_glob = "src/**/*.java"
old = '''        return java.security.acl.Acl.class.getPackageName();'''
new = '''        return "java.security.acl";'''
```
