# Write Ossie documents in Python instead of depending on semglot

`benchouse/semglot` transpiles semantic layers through one neutral IR and treats Ossie as both a source and a target dialect, which makes it the obvious bridge. It is a Go binary, and Trellis ships as a Python wheel. The emitter that produces a valid Ossie document is roughly a hundred lines of dict building, so the exporter is native and `semglot` stays a downstream consumer of the output rather than a dependency.

**Consequences.** No Go toolchain or vendored binary in the install path, and the mapping stays in one module where a spec change is a local edit. The transpile-to-other-tools path is unbuilt: anyone wanting Snowflake semantic views runs `semglot` on the generated file themselves, once `semglot` reads 0.2.0.dev0 (see ADR-0001).

**Considered options.** Shelling out to a pinned `semglot` release would have covered nine output dialects immediately, at the cost of a binary dependency, a version to track, and an error surface we do not control.
