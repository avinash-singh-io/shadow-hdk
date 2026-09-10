# shadow-hdk-adapters-workspace

Four components — `read_file`, `write_file`, `list_dir`, `delete_file` — confined to a root.
Every path is **resolved** before it is checked, so a symlink cannot walk out of the workspace.

`writable=False` removes the writing components rather than refusing them at call time: absent, not
greyed out, which is the rule everywhere else in this design.
