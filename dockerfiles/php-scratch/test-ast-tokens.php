<?php
print("Verifying AST extension matches PHP...
See: https://phabricator.wikimedia.org/T396312#10902917

");

printf(
    <<<TEXT

| Versions     | Constant               | Value
|--------------|------------------------|------
| PHP %-8s | T_CLASS_C              | %s
| AST %-8s | \\ast\\flags\\MAGIC_CLASS | %s

TEXT,
    PHP_VERSION,
    T_CLASS_C,
    phpversion( 'ast' ),
    \ast\flags\MAGIC_CLASS,
);
print("\nVerifying whether T_CLASS_C === \\ast\\flags\\MAGIC_CLASS ... ");
if ( T_CLASS_C !== \ast\flags\MAGIC_CLASS ) {
    print(
        sprintf(
            "error\nERROR: \\ast\\flags\\MAGIC_CLASS value %s does not match PHP T_CLASS_C value: %s\n",
            \ast\flags\MAGIC_CLASS, T_CLASS_C
        )
    );
    exit(1);
} else {
    print("ok\n");
}
