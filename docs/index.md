---
icon: lucide/rocket
---

# sb2git

a tool to convert from a directory of sb3 files
into a git repo so u can put it on e.g. gh

you may start with a directory like this:

```
|- lolpack v1.0.0.sb3
|- lolpack v1.0.1.sb3
|- lolpack v2.0.1.sb3
|- 3d_engine.sb3
|- render.sprite3
|- ...
|- sb2git.toml
```

say this is a project call lolpack. a toolkit for making scratch intros.
The project itself may also include code for a 3d engine,
or separate `sprite3` files

The config of these files is itself written in `sb3git.toml`

running `sb2git init` will initialise the sb2git file by reading from all the files.
It may:

- auto-sort by time modified/created (but you may need to reorder these)

running `sb2git lint` will check for any antipattern-like config,
or recommendations, e.g.:

- map hash names to costume names
- provide groupings of certain sprite3s/sb3s to different branches

sb2git will generate an `instance.toml` file for each commit
to store information about that instance of the project.

`sb2git.toml` should also provide a way of assigning
descriptions/alternate titles to projects.
