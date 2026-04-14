---
name: zip-context
description: "Create a clean project-context zip archive for architecture review, code review, or model handoff. Use when Codex needs to package the current project or repository into a zip while excluding generated files, build output, dependency caches, graphic/media assets, archives, `.gitignore` files, and other noise; or when the user asks to create or update `zip_context_ignore.md`, refresh ignore patterns, or run `zip` or `update` for a project-context archive."
---

# Zip Context

Package a project into a compact zip archive that keeps code, docs, and text configs, while removing project-specific noise discovered by scanning the repository.

## Quick Start

Set the script path once per shell:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export ZIP_CONTEXT="$CODEX_HOME/skills/zip-context/scripts/zip_context.py"
```

Default action is `zip`:

```bash
python3 "$ZIP_CONTEXT"
python3 "$ZIP_CONTEXT" zip
```

Refresh ignore rules only:

```bash
python3 "$ZIP_CONTEXT" update
```

Target another directory:

```bash
python3 "$ZIP_CONTEXT" zip --root /path/to/project
python3 "$ZIP_CONTEXT" update --root /path/to/project
```

## Workflow

1. Resolve the project root. Prefer `git rev-parse --show-toplevel`; otherwise use `--root` or the current directory.
2. Check setup:
   - whether `.gitignore` exists;
   - whether `zip_context_ignore.md` exists.
3. If `zip_context_ignore.md` is missing, scan the project and create it with concrete exclusions:
   - exact build/cache/generated directories that exist in this project;
   - exact generated files and lockfiles that exist in this project;
   - binary-heavy asset directories discovered by inspection;
   - binary/media/archive extensions actually present in this project.
4. If the command is `update`, rescan the project, refresh the auto-detected block, and preserve the manual block.
5. If the command is `zip`, collect candidate files:
   - from git via `git ls-files --cached --others --exclude-standard` when inside a git repo;
   - otherwise by walking the filesystem.
6. Filter candidates by `zip_context_ignore.md`.
7. Exclude probable binary files as a safety net and possible files with keys such as .env files.
8. Write the archive to `output/share/<project>-zip-context-YYYY-MM-DD.zip` unless the user provided `--output`.

## Project Ignore File

The project-local ignore file is always `zip_context_ignore.md` in the project root.

The bundled script maintains two blocks:

- auto-detected exclusions: concrete paths and extensions found in the current project scan;
- manual additions: reserved for extra exclusions that only the user wants.

Only add project-specific custom rules to the manual block. Do not hand-edit the auto-detected block.

## Commands

Use the bundled script:

```bash
python3 "$ZIP_CONTEXT" [zip|update] [--root PATH] [--output PATH]
```

Command semantics:

- `zip`: ensure setup exists, create `zip_context_ignore.md` if needed, then build the archive.
- `update`: rescan the project, rewrite the auto-detected exclusions, and preserve manual additions.

If the user only asks to “zip”, “pack the project”, “prepare context for an architect”, or similar, run `zip`.

## Guardrails

- Prefer the current project root unless the user gave another path.
- Continue even when `.gitignore` is missing; create `zip_context_ignore.md` from the live project scan and still use binary detection as a safety net.
- Exclude `.gitignore` files, the skill's own `zip_context_ignore.md`, dependency caches, build outputs, archives, assets, and generated artifacts unless the user explicitly asks otherwise.
- Keep code, markdown docs, schemas, configs, and text manifests when they are not excluded.
