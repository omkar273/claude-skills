#!/usr/bin/env python3
"""Regenerate the skill catalog table in README.md from every skill's
SKILL.md frontmatter and .origin.yaml. Replaces only the content between
the <!-- CATALOG:START --> and <!-- CATALOG:END --> markers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_meta

START_MARKER = "<!-- CATALOG:START -->"
END_MARKER = "<!-- CATALOG:END -->"


def collect_skills(skills_dir):
    skills_dir = Path(skills_dir)
    rows = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not (skill_dir / "SKILL.md").exists():
            continue
        frontmatter = skill_meta.read_skill_frontmatter(skill_dir)
        origin = skill_meta.read_origin(skill_dir)
        rows.append({
            "name": frontmatter.get("name", skill_dir.name),
            "description": frontmatter.get("description", ""),
            "origin": origin.get("origin", "vendored"),
            "source_repo": origin.get("source_repo", "local"),
        })
    return rows


def render_table(rows):
    lines = ["| Skill | Description | Source |", "| --- | --- | --- |"]
    for row in rows:
        description = row["description"].replace("\n", " ").replace("|", "\\|")
        lines.append(f"| `{row['name']}` | {description} | {row['source_repo']} |")
    return "\n".join(lines)


def render_catalog(rows):
    mine = [r for r in rows if r["origin"] == "mine"]
    vendored = [r for r in rows if r["origin"] != "mine"]
    parts = [
        "### Mine", "", render_table(mine) if mine else "_none yet_", "",
        "### Vendored", "", render_table(vendored) if vendored else "_none yet_",
    ]
    return "\n".join(parts)


def update_readme(readme_path, skills_dir):
    readme_path = Path(readme_path)
    text = readme_path.read_text()
    if START_MARKER not in text or END_MARKER not in text:
        raise ValueError(f"{readme_path} is missing {START_MARKER}/{END_MARKER} markers")
    before, rest = text.split(START_MARKER, 1)
    _, after = rest.split(END_MARKER, 1)
    catalog = render_catalog(collect_skills(skills_dir))
    new_text = f"{before}{START_MARKER}\n\n{catalog}\n\n{END_MARKER}{after}"
    readme_path.write_text(new_text)
    return new_text


def main():
    root = Path(__file__).resolve().parents[2]
    update_readme(root.parent / "README.md", root)
    print("README.md catalog regenerated")


if __name__ == "__main__":
    main()
