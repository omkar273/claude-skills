#!/usr/bin/env python3
"""Scaffold a new skill directory under skills/, with an .origin.yaml
provenance file. Use --seed-from to copy in real content from an existing
skill directory instead of writing a TODO stub."""
import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_meta

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

STUB_TEMPLATE = """---
name: {name}
description: TODO - one-line description of when to use this skill
---

# {title}

TODO: describe what this skill does and how to use it.
"""


def new_skill(name, origin, source_repo="local", source_path="",
              source_ref="", seed_from=None, skills_dir=None):
    if not NAME_RE.match(name):
        raise ValueError(
            f"invalid skill name {name!r}: use lowercase letters, digits, hyphens only"
        )

    skills_dir = Path(skills_dir) if skills_dir else Path(__file__).resolve().parents[2]
    skill_dir = skills_dir / name
    if skill_dir.exists():
        raise FileExistsError(f"skills/{name} already exists")

    if seed_from:
        seed_dir = Path(seed_from)
        if not (seed_dir / "SKILL.md").exists():
            raise FileNotFoundError(f"{seed_dir} has no SKILL.md to seed from")
        shutil.copytree(seed_dir, skill_dir, ignore=shutil.ignore_patterns(".git"))
    else:
        skill_dir.mkdir(parents=True)
        title = name.replace("-", " ").title()
        (skill_dir / "SKILL.md").write_text(STUB_TEMPLATE.format(name=name, title=title))

    skill_meta.write_origin(skill_dir, {
        "origin": origin,
        "source_repo": source_repo,
        "source_path": source_path,
        "source_ref": source_ref,
        "snapshotted_at": datetime.date.today().isoformat(),
    })
    return skill_dir


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="skill directory name, e.g. my-new-skill")
    parser.add_argument("--origin", required=True, choices=["mine", "vendored"])
    parser.add_argument("--source-repo", default="local")
    parser.add_argument("--source-path", default="")
    parser.add_argument("--source-ref", default="")
    parser.add_argument("--seed-from", default=None,
                         help="existing directory to copy SKILL.md and assets from")
    parser.add_argument("--skills-dir", default=None,
                         help="override skills/ location (used by tests)")
    return parser


def main():
    args = build_parser().parse_args()
    skill_dir = new_skill(
        args.name, args.origin, args.source_repo, args.source_path,
        args.source_ref, args.seed_from, args.skills_dir,
    )
    print(f"Created {skill_dir}")
    print("Next: run scripts/gen_catalog.py to refresh README.md")


if __name__ == "__main__":
    main()
