---
name: zip-context
description: "Create a clean project-context zip archive for architecture review, code review, or model handoff. Use when Codex needs to package the current project or repository into a zip while excluding generated files, build output, dependency caches, graphic/media assets, archives, `.gitignore` files, and other noise; when the user wants a focused archive for a specific subsystem or task; or when the user asks to create or update `zip_context_ignore.md`, refresh ignore patterns, or run `zip` or `update` for a project-context archive."
---

# Zip Context

Package a project into a compact zip archive that keeps code, docs, and text configs, while removing project-specific noise discovered by scanning the repository. By default the skill archives the full project. When the user asks for a specific subsystem, feature, task, or bug area, first identify the relevant files and then archive only that scope.

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

Focused archive from a prepared path list:

```bash
python3 "$ZIP_CONTEXT" zip --root /path/to/project --paths-file /tmp/billing-paths.txt
```

## Workflow

1. Resolve the project root. Prefer `git rev-parse --show-toplevel`; otherwise use `--root` or the current directory.
2. Decide whether the request is broad or focused:
   - if the user asks for the full project or gives no scope, use the default full-project archive flow;
   - if the user names a subsystem, feature, task, bug, endpoint, or area such as "billing", first inspect the repo and build a focused list of relevant paths.
3. For a focused request, inspect the repo before zipping:
   - use `rg`, `git ls-files`, existing tests, docs, routes, schemas, configs, migrations, and entrypoints to find the files tied to the request;
   - write a newline-delimited manifest with repo-relative paths or directories;
   - prefer a disposable manifest path such as `/tmp/<scope>-paths.txt`.
4. Check setup:
   - whether `.gitignore` exists;
   - whether `zip_context_ignore.md` exists.
5. If `zip_context_ignore.md` is missing, scan the project and create it with concrete exclusions:
   - exact build/cache/generated directories that exist in this project;
   - exact generated files and lockfiles that exist in this project;
   - binary-heavy asset directories discovered by inspection;
   - binary/media/archive extensions actually present in this project.
6. If the command is `update`, rescan the project, refresh the auto-detected block, and preserve the manual block.
7. If the command is `zip`, choose the candidate source:
   - full-project mode: collect candidates from git via `git ls-files --cached --others --exclude-standard` when inside a git repo, otherwise by walking the filesystem;
   - focused mode: pass the prepared manifest with `--paths-file`.
8. Filter candidates:
   - full-project mode respects `zip_context_ignore.md`;
   - focused mode keeps the explicit scope even if some files live under normally ignored generated/build directories.
9. Exclude probable binary files and secret-like files such as `.env` as a safety net.
10. Write the archive to `output/share/<project>-zip-context-YYYY-MM-DD.zip` unless the user provided `--output`.

## Project Ignore File

The project-local ignore file is always `zip_context_ignore.md` in the project root.

The bundled script maintains two blocks:

- auto-detected exclusions: concrete paths and extensions found in the current project scan;
- manual additions: reserved for extra exclusions that only the user wants.

Only add project-specific custom rules to the manual block. Do not hand-edit the auto-detected block.

## Commands

Use the bundled script:

```bash
python3 "$ZIP_CONTEXT" [zip|update] [--root PATH] [--output PATH] [--paths-file PATH]
```

Command semantics:

- `zip`: ensure setup exists, create `zip_context_ignore.md` if needed, then build the archive.
- `zip --paths-file <file>`: build a focused archive from a prepared newline-delimited list of repo-relative or absolute paths. Directories in the list are expanded recursively.
- `update`: rescan the project, rewrite the auto-detected exclusions, and preserve manual additions.

If the user only asks to “zip”, “pack the project”, “prepare context for an architect”, or similar, run `zip`.
If the user asks for “files of the billing subsystem”, “only auth-related files”, “pack code relevant to this bug”, or similar, first build a focused manifest and then run `zip --paths-file`.

## Guardrails

- Prefer the current project root unless the user gave another path.
- Continue even when `.gitignore` is missing; create `zip_context_ignore.md` from the live project scan and still use binary detection as a safety net.
- For focused requests, include the files that help another model understand the scoped area: entrypoints, handlers, domain logic, schemas, migrations, configs, tests, and nearby docs when they are relevant.
- Do not widen a focused request into a whole-project archive unless the user asked for that broader scope.
- Exclude `.gitignore` files, the skill's own `zip_context_ignore.md`, dependency caches, build outputs, archives, assets, and generated artifacts unless the user explicitly asks otherwise.
- Keep code, markdown docs, schemas, configs, and text manifests when they are not excluded.
