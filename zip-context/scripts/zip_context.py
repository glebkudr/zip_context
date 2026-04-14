#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import date
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath


IGNORE_FILE_NAME = "zip_context_ignore.md"
GENERATED_START = "<!-- zip-context:generated:start -->"
GENERATED_END = "<!-- zip-context:generated:end -->"
EXTRA_START = "<!-- zip-context:extra:start -->"
EXTRA_END = "<!-- zip-context:extra:end -->"
CONTROL_BYTES = {byte for byte in range(32) if byte not in (9, 10, 13)}
PRUNE_SCAN_DIR_NAMES = {
    ".git",
    "node_modules",
    "target",
    ".next",
    ".next-dev",
    ".next-playwright",
    ".next-investigate",
    ".nuxt",
    ".svelte-kit",
    ".parcel-cache",
    ".turbo",
    ".playwright",
    ".playwright-cli",
    ".cache",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".gradle",
    "dist",
    "build",
    "out",
    "output",
    "coverage",
    "tmp",
    "temp",
    "test-results",
    "playwright-report",
}
REPO_METADATA_DIR_NAMES = {".codex", ".hg", ".svn", ".idea", ".vscode"}
BUILD_CACHE_DIR_NAMES = {
    "node_modules",
    "target",
    ".next",
    ".next-dev",
    ".next-playwright",
    ".next-investigate",
    ".nuxt",
    ".svelte-kit",
    ".parcel-cache",
    ".turbo",
    ".playwright",
    ".playwright-cli",
    ".cache",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".gradle",
    "dist",
    "build",
    "out",
    "output",
    "coverage",
    "tmp",
    "temp",
}
GENERATED_DIR_NAMES = {
    "generated",
    "__generated__",
    "generated-fixtures",
    "test-results",
    "playwright-report",
    "snapshots",
    "__snapshots__",
}
SPECIAL_EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}
ASSET_CANDIDATE_DIR_NAMES = {
    "assets",
    "asset",
    "public",
    "static",
    "media",
}
DIRECT_BINARY_DIR_NAMES = {
    "images",
    "sprites",
    "textures",
    "tiles",
    "art",
}
KNOWN_BINARY_EXTENSIONS = {
    ".7z",
    ".a",
    ".avi",
    ".bin",
    ".bmp",
    ".bz2",
    ".class",
    ".cpuprofile",
    ".dll",
    ".dylib",
    ".eot",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".o",
    ".ogg",
    ".otf",
    ".pdf",
    ".png",
    ".profdata",
    ".profraw",
    ".rar",
    ".so",
    ".tar",
    ".tgz",
    ".tif",
    ".tiff",
    ".ttf",
    ".wav",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".xz",
    ".zip",
}


@dataclass(frozen=True)
class ProjectSetup:
    root: Path
    is_git_repo: bool
    has_gitignore: bool
    ignore_file: Path


@dataclass(frozen=True)
class ProjectScan:
    files: list[Path]
    dirs: list[Path]


@dataclass(frozen=True)
class IgnoreState:
    ignore_file: Path
    generated_patterns: list[str]
    extra_patterns: list[str]
    action: str


@dataclass(frozen=True)
class SelectionStats:
    candidate_paths: int
    included_paths: int
    ignored_paths: int
    binary_paths: int
    missing_paths: int


@dataclass(frozen=True)
class SelectionResult:
    relative_paths: list[Path]
    stats: SelectionStats


@dataclass(frozen=True)
class ArchiveSummary:
    output_path: Path
    file_count: int
    archive_size_bytes: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create or refresh a clean project-context zip archive. Default command: zip."
        ),
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("zip", "update"),
        default="zip",
        help="`zip` builds the archive; `update` refreshes the ignore file only.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project path. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Archive path for the `zip` command.",
    )
    parser.add_argument(
        "--paths-file",
        type=Path,
        help=(
            "Optional newline-delimited file with repo-relative or absolute paths to package. "
            "Useful when the agent already identified files related to a specific task or subsystem."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    setup = inspect_project(args.root.resolve())
    force_regenerate = args.command == "update"
    ignore_state = ensure_ignore_file(setup, force_regenerate=force_regenerate)

    print(f"project root: {setup.root}")
    print(f"git repo: {'yes' if setup.is_git_repo else 'no'}")
    print(f".gitignore: {'found' if setup.has_gitignore else 'missing'}")
    print(f"{IGNORE_FILE_NAME}: {ignore_state.action}")

    if args.command == "update":
        return 0

    output_path = args.output.resolve() if args.output else default_output_path(setup.root)
    extra_ignored_paths = [Path(IGNORE_FILE_NAME)]
    if args.paths_file is not None:
        try:
            extra_ignored_paths.append(args.paths_file.resolve().relative_to(setup.root))
        except ValueError:
            pass
    try:
        extra_ignored_paths.append(output_path.relative_to(setup.root))
    except ValueError:
        pass

    if args.paths_file is not None:
        try:
            explicit_candidates, explicit_missing_paths = load_explicit_candidate_paths(
                root=setup.root,
                paths_file=args.paths_file.resolve(),
            )
        except (FileNotFoundError, ValueError) as exc:
            sys.stderr.write(f"{exc}\n")
            return 1

        print(f"selection mode: focused ({args.paths_file.resolve()})")
        selection = select_project_files(
            setup=setup,
            ignore_patterns=ignore_state.generated_patterns + ignore_state.extra_patterns,
            extra_ignored_paths=extra_ignored_paths,
            candidate_paths=explicit_candidates,
            apply_ignore_patterns=False,
            initial_missing_paths=explicit_missing_paths,
        )
    else:
        print("selection mode: full project")
        selection = select_project_files(
            setup=setup,
            ignore_patterns=ignore_state.generated_patterns + ignore_state.extra_patterns,
            extra_ignored_paths=extra_ignored_paths,
        )
    if not selection.relative_paths:
        sys.stderr.write("no files selected for the zip-context archive\n")
        return 1

    summary = write_archive(
        repo_root=setup.root,
        relative_paths=selection.relative_paths,
        output_path=output_path,
    )
    print(f"candidates: {selection.stats.candidate_paths}")
    print(f"included: {selection.stats.included_paths}")
    print(f"ignored by patterns: {selection.stats.ignored_paths}")
    print(f"ignored as binary: {selection.stats.binary_paths}")
    print(f"missing on disk: {selection.stats.missing_paths}")
    print(f"archive: {summary.output_path}")
    print(f"archive files: {summary.file_count}")
    print(f"archive size: {summary.archive_size_bytes} bytes")
    return 0


def inspect_project(start_path: Path) -> ProjectSetup:
    git_root = resolve_git_root(start_path)
    root = git_root if git_root is not None else start_path
    return ProjectSetup(
        root=root,
        is_git_repo=git_root is not None,
        has_gitignore=(root / ".gitignore").is_file(),
        ignore_file=root / IGNORE_FILE_NAME,
    )


def resolve_git_root(path: Path) -> Path | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            check=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return Path(completed.stdout.strip()).resolve()


def default_output_path(root: Path) -> Path:
    archive_name = f"{root.name}-zip-context-{date.today().isoformat()}.zip"
    return root / "output" / "share" / archive_name


def ensure_ignore_file(setup: ProjectSetup, force_regenerate: bool) -> IgnoreState:
    generated_patterns = build_generated_patterns(setup.root)
    if not setup.ignore_file.exists():
        write_ignore_file(
            path=setup.ignore_file,
            generated_patterns=generated_patterns,
            extra_patterns=[],
        )
        return IgnoreState(
            ignore_file=setup.ignore_file,
            generated_patterns=generated_patterns,
            extra_patterns=[],
            action="created",
        )

    parsed = parse_ignore_file(setup.ignore_file)
    if parsed is None:
        write_ignore_file(
            path=setup.ignore_file,
            generated_patterns=generated_patterns,
            extra_patterns=[],
        )
        return IgnoreState(
            ignore_file=setup.ignore_file,
            generated_patterns=generated_patterns,
            extra_patterns=[],
            action="replaced-invalid-format",
        )

    parsed_generated_patterns, extra_patterns = parsed
    if force_regenerate:
        write_ignore_file(
            path=setup.ignore_file,
            generated_patterns=generated_patterns,
            extra_patterns=extra_patterns,
        )
        return IgnoreState(
            ignore_file=setup.ignore_file,
            generated_patterns=generated_patterns,
            extra_patterns=extra_patterns,
            action="updated",
        )

    return IgnoreState(
        ignore_file=setup.ignore_file,
        generated_patterns=parsed_generated_patterns,
        extra_patterns=extra_patterns,
        action="found",
    )


def build_generated_patterns(root: Path) -> list[str]:
    scan = scan_project_tree(root)
    patterns: list[str] = []

    add_section(
        patterns,
        "Always exclude repository internals and local helper files",
        [".git/", IGNORE_FILE_NAME],
    )
    add_section(
        patterns,
        "Found in this project: local metadata and editor noise",
        [*select_existing_dirs(scan, REPO_METADATA_DIR_NAMES), *select_existing_special_files(scan)],
    )
    add_section(
        patterns,
        "Found in this project: .gitignore and lockfiles",
        [*select_existing_gitignore_files(scan), *select_existing_lockfiles(scan)],
    )
    add_section(
        patterns,
        "Found in this project: build, cache, and generated directories",
        [
            *select_existing_dirs(scan, BUILD_CACHE_DIR_NAMES),
            *select_generated_directories(scan),
        ],
    )

    add_section(
        patterns,
        "Found in this project: generated files and local artifacts",
        select_generated_files(scan),
    )

    asset_subtree_patterns = discover_binary_asset_subtrees(root)
    if asset_subtree_patterns:
        add_section(
            patterns,
            "Found in this project: binary-heavy asset directories",
            asset_subtree_patterns,
        )

    binary_extension_globs = collect_detected_binary_extension_globs(scan)
    if binary_extension_globs:
        add_section(
            patterns,
            "Detected binary/media/archive extensions in this project",
            binary_extension_globs,
        )

    env_files = select_env_files(scan)
    if env_files:
        add_section(
            patterns,
            "Found in this project: env or secret-like files",
            env_files,
        )

    return patterns


def add_section(patterns: list[str], title: str, section_patterns: list[str]) -> None:
    filtered_patterns = unique_preserve_order(section_patterns)
    if not filtered_patterns:
        return
    if patterns:
        patterns.append("")
    patterns.append(f"# {title}")
    patterns.extend(filtered_patterns)


def scan_project_tree(root: Path) -> ProjectScan:
    files: list[Path] = []
    dirs: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        current_root_path = Path(current_root)
        try:
            current_relative = current_root_path.relative_to(root)
        except ValueError:
            continue

        kept_dirnames: list[str] = []
        for dirname in sorted(dirnames):
            relative_dir = (current_relative / dirname) if current_relative != Path(".") else Path(dirname)
            dirs.append(relative_dir)
            if dirname in PRUNE_SCAN_DIR_NAMES:
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in sorted(filenames):
            relative_file = (current_relative / filename) if current_relative != Path(".") else Path(filename)
            files.append(relative_file)

    dirs.sort(key=lambda path: path.as_posix())
    files.sort(key=lambda path: path.as_posix())
    return ProjectScan(files=files, dirs=dirs)


def select_existing_dirs(scan: ProjectScan, names: set[str]) -> list[str]:
    return [f"{path.as_posix()}/" for path in scan.dirs if path.name in names]


def select_existing_special_files(scan: ProjectScan) -> list[str]:
    return [
        path.as_posix()
        for path in scan.files
        if path.name in SPECIAL_EXCLUDED_FILE_NAMES or path.name in {".DS_Store", "Thumbs.db"}
    ] + ["*.swp", "*.swo"]


def select_existing_gitignore_files(scan: ProjectScan) -> list[str]:
    return [path.as_posix() for path in scan.files if path.name == ".gitignore" or path.name.endswith(".gitignore")]


def select_existing_lockfiles(scan: ProjectScan) -> list[str]:
    return [path.as_posix() for path in scan.files if path.name in {"Cargo.lock", "pnpm-lock.yaml", "yarn.lock", "package-lock.json", "bun.lockb"}]


def select_generated_directories(scan: ProjectScan) -> list[str]:
    return [
        f"{path.as_posix()}/"
        for path in scan.dirs
        if path.name in GENERATED_DIR_NAMES or path.name.endswith("-snapshots")
    ]


def select_generated_files(scan: ProjectScan) -> list[str]:
    patterns: list[str] = []
    for path in scan.files:
        path_string = path.as_posix()
        if path.name == "next-env.d.ts":
            patterns.append(path_string)
            continue
        if path.suffix in {".snap", ".cpuprofile", ".profraw", ".profdata", ".tsbuildinfo", ".tiled-session"}:
            patterns.append(path_string)
            continue
        if path_string.endswith(".min.js") or path_string.endswith(".min.css"):
            patterns.append(path_string)
    return patterns


def collect_detected_binary_extension_globs(scan: ProjectScan) -> list[str]:
    extensions = sorted(
        {
            f"*{path.suffix}"
            for path in scan.files
            if path.suffix and path.suffix.lower() in KNOWN_BINARY_EXTENSIONS
        },
        key=lambda value: value.lower(),
    )
    return extensions


def select_env_files(scan: ProjectScan) -> list[str]:
    patterns: list[str] = []
    for path in scan.files:
        name = path.name.lower()
        if not name.startswith(".env"):
            continue
        if name in {".env.example", ".env.sample", ".env.template", ".env.dist"}:
            continue
        patterns.append(path.as_posix())
    return patterns


def unique_preserve_order(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def load_explicit_candidate_paths(root: Path, paths_file: Path) -> tuple[list[Path], int]:
    if not paths_file.is_file():
        raise FileNotFoundError(f"paths file not found: {paths_file}")

    relative_paths: list[Path] = []
    seen: set[str] = set()
    missing_paths = 0

    for raw_line in paths_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        target = resolve_manifest_target(root=root, raw_path=line)
        if target is None:
            missing_paths += 1
            continue

        for relative_path in expand_manifest_target(root=root, target=target):
            path_string = relative_path.as_posix()
            if path_string in seen:
                continue
            seen.add(path_string)
            relative_paths.append(relative_path)

    return relative_paths, missing_paths


def resolve_manifest_target(root: Path, raw_path: str) -> Path | None:
    candidate = Path(raw_path)
    absolute_target = candidate if candidate.is_absolute() else (root / candidate)
    absolute_target = absolute_target.resolve()

    try:
        absolute_target.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"paths file entry points outside project root: {raw_path}"
        ) from exc

    if not absolute_target.exists():
        return None

    return absolute_target


def expand_manifest_target(root: Path, target: Path) -> list[Path]:
    if target.is_file():
        return [target.relative_to(root)]

    if not target.is_dir():
        return []

    relative_paths: list[Path] = []
    for child in sorted(target.rglob("*")):
        if child.is_file():
            relative_paths.append(child.relative_to(root))
    return relative_paths


def should_exclude_secret_path(relative_path: Path) -> bool:
    name = relative_path.name.lower()
    if name.startswith(".env") and name not in {
        ".env.example",
        ".env.sample",
        ".env.template",
        ".env.dist",
    }:
        return True
    if name in {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}:
        return True
    if relative_path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
        return True
    return False


def discover_binary_asset_subtrees(root: Path) -> list[str]:
    candidates: list[Path] = []
    seen_candidates: set[Path] = set()

    for child in root.iterdir():
        if not child.is_dir():
            continue
        if child.name in ASSET_CANDIDATE_DIR_NAMES:
            for nested in child.iterdir():
                if nested.is_dir() and nested not in seen_candidates:
                    seen_candidates.add(nested)
                    candidates.append(nested)
            continue
        if child.name in DIRECT_BINARY_DIR_NAMES and child not in seen_candidates:
            seen_candidates.add(child)
            candidates.append(child)

    patterns: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not is_binary_heavy_directory(candidate):
            continue
        relative = candidate.relative_to(root).as_posix() + "/"
        if relative in seen:
            continue
        seen.add(relative)
        patterns.append(relative)
    return patterns


def is_binary_heavy_directory(path: Path) -> bool:
    binary_count = 0
    text_count = 0
    sample_budget = 200

    for child in path.rglob("*"):
        if sample_budget <= 0:
            break
        if not child.is_file():
            continue
        sample_budget -= 1
        if is_probably_binary(child):
            binary_count += 1
        else:
            text_count += 1

    if binary_count == 0:
        return False
    return text_count == 0 or binary_count >= (text_count * 3)


def parse_ignore_file(path: Path) -> tuple[list[str], list[str]] | None:
    text = path.read_text(encoding="utf-8")
    generated_block = extract_marked_block(text, GENERATED_START, GENERATED_END)
    extra_block = extract_marked_block(text, EXTRA_START, EXTRA_END)
    if generated_block is None or extra_block is None:
        return None
    return parse_patterns_block(generated_block), parse_patterns_block(extra_block)


def extract_marked_block(text: str, start_marker: str, end_marker: str) -> str | None:
    pattern = re.compile(
        rf"{re.escape(start_marker)}\s*```[^\n]*\n(.*?)\n```\s*{re.escape(end_marker)}",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        return None
    return match.group(1)


def parse_patterns_block(block: str) -> list[str]:
    patterns: list[str] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def write_ignore_file(path: Path, generated_patterns: list[str], extra_patterns: list[str]) -> None:
    path.write_text(
        render_ignore_file(generated_patterns=generated_patterns, extra_patterns=extra_patterns),
        encoding="utf-8",
    )


def render_ignore_file(generated_patterns: list[str], extra_patterns: list[str]) -> str:
    generated_block = "\n".join(generated_patterns) if generated_patterns else "# no detected exclusions"
    extra_block = "\n".join(extra_patterns) if extra_patterns else "# add project-specific patterns here"
    return (
        "# Zip Context Ignore\n\n"
        "This file is produced by a project scan from the global `zip-context` skill.\n\n"
        "- The first block contains concrete exclusions detected in this project.\n"
        "- The second block is for manual project-specific additions.\n"
        "- Run `update` when the project layout changes and you want to rescan it.\n\n"
        "## Auto-Detected Exclusions\n"
        f"{GENERATED_START}\n"
        "```ignore\n"
        f"{generated_block}\n"
        "```\n"
        f"{GENERATED_END}\n\n"
        "## Manual Additions\n"
        f"{EXTRA_START}\n"
        "```ignore\n"
        f"{extra_block}\n"
        "```\n"
        f"{EXTRA_END}\n"
    )


def select_project_files(
    setup: ProjectSetup,
    ignore_patterns: list[str],
    extra_ignored_paths: list[Path] | None = None,
    candidate_paths: list[Path] | None = None,
    apply_ignore_patterns: bool = True,
    initial_missing_paths: int = 0,
) -> SelectionResult:
    candidates = candidate_paths if candidate_paths is not None else list_candidate_files(setup, ignore_patterns)
    ignored_exact = {path.as_posix() for path in extra_ignored_paths or []}
    relative_paths: list[Path] = []
    ignored_paths = 0
    binary_paths = 0
    missing_paths = initial_missing_paths
    seen: set[str] = set()

    for relative_path in candidates:
        path_string = relative_path.as_posix()
        absolute_path = setup.root / relative_path
        if path_string in seen:
            continue
        seen.add(path_string)

        if path_string in ignored_exact:
            ignored_paths += 1
            continue
        if not absolute_path.is_file():
            missing_paths += 1
            continue
        if should_exclude_secret_path(relative_path):
            ignored_paths += 1
            continue
        if apply_ignore_patterns and should_ignore_path(path_string, ignore_patterns):
            ignored_paths += 1
            continue
        if is_probably_binary(absolute_path):
            binary_paths += 1
            continue

        relative_paths.append(relative_path)

    relative_paths.sort(key=lambda path: path.as_posix())
    return SelectionResult(
        relative_paths=relative_paths,
        stats=SelectionStats(
            candidate_paths=len(seen) + initial_missing_paths,
            included_paths=len(relative_paths),
            ignored_paths=ignored_paths,
            binary_paths=binary_paths,
            missing_paths=missing_paths,
        ),
    )


def list_candidate_files(setup: ProjectSetup, ignore_patterns: list[str]) -> list[Path]:
    if setup.is_git_repo:
        return git_ls_files(setup.root)
    return walk_filesystem(setup.root, ignore_patterns)


def git_ls_files(repo_root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    paths: list[Path] = []
    seen: set[str] = set()
    for raw_path in completed.stdout.split(b"\0"):
        if not raw_path:
            continue
        decoded_path = raw_path.decode("utf-8")
        if decoded_path in seen:
            continue
        seen.add(decoded_path)
        paths.append(Path(decoded_path))
    return paths


def walk_filesystem(root: Path, ignore_patterns: list[str]) -> list[Path]:
    relative_paths: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        current_root_path = Path(current_root)
        current_relative = current_root_path.relative_to(root)

        filtered_dirnames: list[str] = []
        for dirname in dirnames:
            relative_dir = (current_relative / dirname) if current_relative != Path(".") else Path(dirname)
            if should_ignore_path(f"{relative_dir.as_posix()}/", ignore_patterns):
                continue
            filtered_dirnames.append(dirname)
        dirnames[:] = filtered_dirnames

        for filename in filenames:
            relative_path = (current_relative / filename) if current_relative != Path(".") else Path(filename)
            if should_ignore_path(relative_path.as_posix(), ignore_patterns):
                continue
            relative_paths.append(relative_path)
    return relative_paths


def should_ignore_path(path_string: str, ignore_patterns: list[str]) -> bool:
    path_name = PurePosixPath(path_string).name
    path_parts = PurePosixPath(path_string).parts

    for pattern in ignore_patterns:
        if pattern.endswith("/"):
            directory = pattern.rstrip("/")
            if "/" in directory:
                if path_string == directory or path_string.startswith(f"{directory}/"):
                    return True
                continue
            if directory in path_parts:
                return True
            continue

        if any(char in pattern for char in "*?["):
            if fnmatchcase(path_string, pattern) or fnmatchcase(path_name, pattern):
                return True
            continue

        if "/" in pattern:
            if path_string == pattern:
                return True
            continue

        if path_string == pattern or path_name == pattern:
            return True

    return False


def is_probably_binary(path: Path, sample_size: int = 8192) -> bool:
    if path.suffix.lower() in KNOWN_BINARY_EXTENSIONS:
        return True
    sample = path.read_bytes()[:sample_size]
    if not sample:
        return False
    if b"\0" in sample:
        return True
    return any(byte in CONTROL_BYTES for byte in sample)


def write_archive(repo_root: Path, relative_paths: list[Path], output_path: Path) -> ArchiveSummary:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for relative_path in relative_paths:
            archive.write(repo_root / relative_path, arcname=relative_path.as_posix())

    return ArchiveSummary(
        output_path=output_path,
        file_count=len(relative_paths),
        archive_size_bytes=output_path.stat().st_size,
    )


if __name__ == "__main__":
    raise SystemExit(main())
