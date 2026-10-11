# Validation and Error Handling

## Discover commands dynamically

Never hard-code build/test/lint commands without repository evidence.

Discover them from manifests, workspace configs, Makefile/justfile/Taskfile, Cargo.toml, pyproject.toml, requirements/tox configs, Maven/Gradle, go.mod, CMakeLists.txt, project.godot, .NET project files, pubspec.yaml, Docker configs, CI workflows, scripts, and docs.

Determine actual build, test, unit/integration/E2E, lint, type-check, formatting, smoke-test, and packaging commands.

Prefer commands already used by CI or project docs.

## Framework/toolchain handling

Inspect detected technology's own configuration and follow existing conventions.

Examples are guidance only:
- Angular: workspace config and project boundaries.
- Svelte/SvelteKit: config, routes, adapters.
- Rust: Cargo workspace, crates, features, build scripts.
- Tauri: frontend/Rust boundary and `src-tauri`.
- Godot: project.godot, scenes, scripts, resources, autoloads, signals.
- Unknown framework: inspect configs/source and infer conventions.

## Validation behavior

- Use the smallest meaningful checks.
- Broaden validation when risk or shared dependencies justify it.
- Add regression tests when useful.
- Do not claim success unless actually verified.

## Error handling

When validation fails:

1. inspect the real error;
2. determine whether it is newly introduced or pre-existing;
3. fix introduced failures;
4. avoid masking unrelated failures;
5. document unresolved existing failures when relevant.
