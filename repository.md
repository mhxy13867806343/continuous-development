# Repository Discovery and Architecture

## Repository-first rule

Never assume the repository uses a specific language, framework, runtime, package manager, database, ORM, build system, test framework, CI system, deployment system, architecture, or module layout.

Inspect the repository first.

## Read project instructions

Look for `AGENTS.md`, `README*`, `CONTRIBUTING*`, `DEVELOPMENT*`, `docs/`, `TODO*`, `ROADMAP*`, `PROGRESS*`, `CHANGELOG*`, architecture/design documents, manifests, workspace files, compiler/build/framework configs, and CI workflows.

Repository-specific instructions override generic assumptions.

## Detect technologies dynamically

Possible technologies include JavaScript/TypeScript, Angular, Vue, React, Svelte, SvelteKit, Solid, Qwik, Astro, Next.js, Nuxt, Node.js, Bun, Deno, Python, FastAPI, Django, Flask, Go, Rust, Axum, Actix, Tauri, Java, Kotlin, Spring, C/C++/C#/.NET, Godot, Unity, Flutter/Dart, React Native, Electron, Android/iOS, CLI tools, libraries, servers, APIs, databases, and infrastructure repositories.

This list is illustrative only.

If a technology is unfamiliar, infer conventions from repository evidence.

## Architecture mapping

Build an internal map of real boundaries such as applications, services, packages, crates, modules, features, domains, layers, components, plugins, renderer/runtime boundaries, API/persistence/infrastructure, shared libraries, game systems, desktop processes, editor tooling, and test suites.

Do not invent artificial boundaries.

## Current state inspection

At the beginning of each round inspect:

- current branch
- git status
- git diff
- staged changes
- untracked files
- remotes/upstream
- recent commits
- TODO/FIXME
- progress docs
- failing builds/tests
- compiler/type/lint/runtime errors
- incomplete features
- pending integration work

Preserve unrelated local user changes.

## Backlog discovery

Build a real backlog from the explicit user request, TODO/FIXME, failures, incomplete implementations, placeholders, missing integrations, unfinished UI/APIs, roadmap/progress docs, comments, missing edge-case handling, incomplete tests, and relevant documentation gaps.

Priority:

1. explicit user request
2. blockers
3. broken core functionality
4. regressions
5. incomplete existing features
6. correctness
7. reliability
8. tests
9. documentation
10. lower-priority improvements

Do not invent speculative features just to remain busy.
