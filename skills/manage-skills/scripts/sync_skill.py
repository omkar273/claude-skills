#!/usr/bin/env python3
"""Refresh a skill's content from its recorded .origin.yaml source.

Local filesystem sources (source_repo is a path) are copied directly.
Remote sources (source_repo is a git URL) are shallow-cloned into a
scratch directory first. source_repo == 'local' means nothing to sync.
"""
import argparse
import datetime
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_meta


def is_remote(source_repo):
    return (
        source_repo.startswith("http://")
        or source_repo.startswith("https://")
        or source_repo.startswith("git@")
    )


def clone_shallow(url, dest):
    subprocess.run(["git", "clone", "--depth", "1", url, str(dest)], check=True)


def git_short_head(path):
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def resolve_source_dir(origin, workdir, clone=clone_shallow):
    """Returns (source_dir, git_root). git_root is set only when the
    source was freshly cloned (its HEAD sha is meaningful as a new
    source_ref); it's None for local filesystem sources."""
    source_repo = origin.get("source_repo", "local")
    if source_repo == "local" or not source_repo:
        return None, None
    if is_remote(source_repo):
        dest = Path(workdir) / "clone"
        clone(source_repo, dest)
        base, git_root = dest, dest
    else:
        base = Path(source_repo).expanduser()
        if not base.exists():
            raise FileNotFoundError(f"source_repo path does not exist: {base}")
        git_root = None
    source_path = origin.get("source_path", "")
    src = base / source_path if source_path else base
    return src, git_root


def sync_one(skill_dir, new_ref=None, workdir_root=None, clone=clone_shallow,
             get_head=git_short_head):
    skill_dir = Path(skill_dir)
    origin = skill_meta.read_origin(skill_dir)
    source_repo = origin.get("source_repo", "local")

    if source_repo == "local" or not source_repo:
        print(f"{skill_dir.name}: source_repo is 'local', nothing to sync")
        return False

    with tempfile.TemporaryDirectory(dir=workdir_root) as workdir:
        src, git_root = resolve_source_dir(origin, workdir, clone=clone)
        if not src.exists():
            raise FileNotFoundError(f"resolved source path does not exist: {src}")

        shutil.copytree(src, skill_dir, dirs_exist_ok=True,
                         ignore=shutil.ignore_patterns(".git"))

        if new_ref:
            origin["source_ref"] = new_ref
        elif git_root:
            origin["source_ref"] = get_head(git_root)
        origin["snapshotted_at"] = datetime.date.today().isoformat()
        skill_meta.write_origin(skill_dir, origin)
        print(f"{skill_dir.name}: synced from {source_repo}")
        return True


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", nargs="?", help="skill directory name to sync")
    parser.add_argument("--all", action="store_true", help="sync every non-local skill")
    parser.add_argument("--ref", default=None, help="explicit source_ref to record")
    parser.add_argument("--skills-dir", default=None)
    return parser


def main():
    args = build_parser().parse_args()
    if not args.all and not args.name:
        sys.exit("error: provide a skill name or --all")
    if args.all and args.name:
        sys.exit("error: provide either a skill name or --all, not both")

    skills_dir = Path(args.skills_dir) if args.skills_dir \
        else Path(__file__).resolve().parents[2]

    if args.all:
        targets = [p for p in sorted(skills_dir.iterdir()) if (p / "SKILL.md").exists()]
    else:
        targets = [skills_dir / args.name]

    for skill_dir in targets:
        sync_one(skill_dir, new_ref=args.ref)


if __name__ == "__main__":
    main()
