"""Minimal metadata readers/writers for this repo's skills.

Two different parsers, because they serve different trust levels:
- parse_kv_block / format_kv_block: for .origin.yaml, which this repo's own
  tooling always writes in a fixed flat 'key: value' shape. No quoting, no
  block scalars.
- parse_frontmatter: for SKILL.md frontmatter, which is authored by many
  different tools/people and commonly uses quoted values or YAML folded
  block scalars (`key: >`) for long descriptions. This is NOT a general
  YAML parser - it only handles the subset seen in this repo's skills.
"""
import re
from pathlib import Path


def parse_kv_block(text):
    """Parse flat 'key: value' lines into a dict, splitting only on the
    FIRST ':' so values containing ':' (like URLs) stay intact. Blank
    lines and '#' comments are ignored. An empty value (e.g. 'key:' or
    'key: ') parses to '' rather than being dropped."""
    result = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip()
    return result


def format_kv_block(data):
    """Format a dict into 'key: value' lines, in insertion order."""
    return "\n".join(f"{key}: {value}" for key, value in data.items()) + "\n"


def read_origin(skill_dir):
    path = Path(skill_dir) / ".origin.yaml"
    return parse_kv_block(path.read_text())


def write_origin(skill_dir, data):
    path = Path(skill_dir) / ".origin.yaml"
    ordered = {
        "origin": data["origin"],
        "source_repo": data.get("source_repo", "local"),
        "source_path": data.get("source_path", ""),
        "source_ref": data.get("source_ref", ""),
        "snapshotted_at": data["snapshotted_at"],
    }
    path.write_text(format_kv_block(ordered))


_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(.*)$")


def parse_frontmatter(text):
    """Parse a SKILL.md frontmatter block. Supports plain 'key: value'
    lines, double-quoted values, and YAML folded ('>') or literal ('|')
    block scalars for multi-line descriptions."""
    result = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        match = _KEY_RE.match(line)
        if not match:
            i += 1
            continue
        key, rest = match.group(1), match.group(2).strip()
        if rest in (">", "|"):
            i += 1
            block_lines = []
            while i < len(lines) and (lines[i].strip() == "" or lines[i][:1] in (" ", "\t")):
                block_lines.append(lines[i].strip())
                i += 1
            if rest == ">":
                result[key] = " ".join(l for l in block_lines if l)
            else:
                result[key] = "\n".join(block_lines).strip()
            continue
        if len(rest) >= 2 and rest[0] == rest[-1] == '"':
            rest = rest[1:-1]
        result[key] = rest
        i += 1
    return result


def read_skill_frontmatter(skill_dir):
    path = Path(skill_dir) / "SKILL.md"
    text = path.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{path} has no frontmatter block")
    return parse_frontmatter(parts[1])
