#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

EXCLUDE = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".cache",
    "Library",
    ".Trash",
    ".cursor",
    ".Cursor",
    "Applications",
}

HOOK_FILES = ("_identity_guard.py", "pre-commit", "commit-msg", "pre-push")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install git information-loss guard hooks into many repos.")
    parser.add_argument(
        "--source",
        default=str(Path(__file__).resolve().parent / "hooks"),
        help="Directory containing hook templates.",
    )
    parser.add_argument(
        "--roots",
        nargs="+",
        required=True,
        help="Root directories to scan for git repositories.",
    )
    parser.add_argument("--max-depth", type=int, default=6, help="Maximum directory depth to scan.")
    return parser.parse_args()


def discover_repos(roots: list[Path], max_depth: int) -> list[Path]:
    repos: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        stack: list[tuple[Path, int]] = [(root, 0)]
        while stack:
            cur, depth = stack.pop()
            if depth > max_depth:
                continue
            try:
                with os.scandir(cur) as it:
                    entries = list(it)
            except Exception:
                continue

            dirs = [e for e in entries if e.is_dir(follow_symlinks=False)]
            names = {e.name for e in dirs}
            if ".git" in names:
                repos.add(cur)
                continue

            for d in dirs:
                if d.name in EXCLUDE:
                    continue
                stack.append((Path(d.path), depth + 1))
    return sorted(repos)


def make_exec(path: Path) -> None:
    path.chmod(path.stat().st_mode | 0o111)


def install_wrapper(hooks_dir: Path, hook_name: str, src: Path) -> None:
    target = hooks_dir / hook_name
    backup = hooks_dir / f"{hook_name}.local"
    if target.exists() and not backup.exists():
        target.rename(backup)
    shutil.copy2(src, target)
    make_exec(target)


def install_repo(repo: Path, source: Path) -> None:
    hooks_dir = repo / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    guard_src = source / "_identity_guard.py"
    guard_dst = hooks_dir / "_identity_guard.py"
    shutil.copy2(guard_src, guard_dst)
    make_exec(guard_dst)

    install_wrapper(hooks_dir, "pre-commit", source / "pre-commit")
    install_wrapper(hooks_dir, "commit-msg", source / "commit-msg")
    install_wrapper(hooks_dir, "pre-push", source / "pre-push")


def main() -> int:
    args = parse_args()
    source = Path(args.source).resolve()
    if not source.exists():
        print(f"Source hooks directory does not exist: {source}")
        return 1
    for name in HOOK_FILES:
        if not (source / name).exists():
            print(f"Missing hook template: {source / name}")
            return 1

    roots = [Path(p).expanduser().resolve() for p in args.roots]
    repos = discover_repos(roots, args.max_depth)

    installed = 0
    failed: list[tuple[str, str]] = []
    for repo in repos:
        try:
            install_repo(repo, source)
            installed += 1
        except Exception as exc:
            failed.append((str(repo), str(exc)))

    print(f"Installed hooks in {installed} repos")
    if failed:
        print(f"Failed in {len(failed)} repos")
        for repo, err in failed:
            print(f"ERR {repo}: {err}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
