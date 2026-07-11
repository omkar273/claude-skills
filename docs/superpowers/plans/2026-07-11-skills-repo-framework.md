# Skills Repo Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the empty `claude-skills` repo into a plugin-ready personal skills library: a flat `skills/` directory holding both self-written ("mine") and curated third-party ("vendored") skills, each tagged with provenance metadata, plus a `manage-skills` tool for scaffolding, syncing, and cataloging.

**Architecture:** `skills/` stays physically flat (one level deep — `skills/<name>/SKILL.md`) because that's what Claude Code plugin discovery requires; "mine vs. vendored" is tracked via a per-skill `.origin.yaml` file instead of folder nesting. A new `manage-skills` skill under `skills/manage-skills/` ships three small stdlib-only Python scripts (`new_skill.py`, `sync_skill.py`, `gen_catalog.py`) that scaffold, refresh, and catalog skills mechanically. Initial content is migrated in by seeding `new_skill.py` from real local sources (the `flexprice-claude-plugin` repo, the `superpowers` marketplace clone, and the local design/`graphify` skill folders).

**Tech Stack:** Python 3 standard library only (`argparse`, `pathlib`, `shutil`, `subprocess`, `tempfile`, `re`, `unittest`) — no external dependencies, no `pip install` step. Tests run with `python3 -m unittest`.

**Run every command in this plan from the repo root: `/Users/omkar/Developer/source-code/claude-skills`.**

---

## Design notes carried over from the spec

- `.origin.yaml` schema (5 fixed fields): `origin` (`mine`|`vendored`), `source_repo` (a URL, a local filesystem path, or the sentinel `local` meaning "no repo tracks this"), `source_path` (subpath within that source, often empty), `source_ref` (commit/version snapshotted, often empty), `snapshotted_at` (`YYYY-MM-DD`).
- Real `SKILL.md` files in this migration use two different frontmatter styles: the 6 Flexprice ("mine") skills all use a YAML **folded block scalar** (`description: >` followed by indented continuation lines), while the superpowers/design/graphify skills use a plain single-line or quoted `description: value`. The catalog generator's frontmatter reader must handle both, or the Flexprice skills' descriptions will silently come out wrong in `README.md`.
- Confirmed source commits to record: `flexprice/claude-plugin` is at `c4cd3f7` (local checkout: `/Users/omkar/Developer/source-code/flexprice/flexprice-claude-plugin`); the `superpowers` marketplace clone is at `b557648` (local checkout: `/Users/omkar/.claude/plugins/marketplaces/superpowers-dev`), upstream `https://github.com/obra/superpowers`.

---

### Task 1: Repo skeleton

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `README.md`
- Modify: `.gitignore`

- [ ] **Step 1: Write the plugin manifest**

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "claude-skills",
  "description": "Personal library of Claude Code skills — self-written and curated third-party.",
  "version": "0.1.0",
  "skills": "./skills/"
}
```

- [ ] **Step 2: Write the README skeleton**

Create `README.md`:

```markdown
# claude-skills

Personal library of Claude Code skills: skills I wrote myself, and third-party skills I rely on, snapshotted into one place. Structured to be installable as a Claude Code plugin (`claude plugin add`).

Every skill folder under `skills/` carries a `.origin.yaml` recording where its content came from. See [`skills/manage-skills`](skills/manage-skills/SKILL.md) for how to add, sync, and re-catalog skills in this repo.

## Skills

<!-- CATALOG:START -->

_run `python3 skills/manage-skills/scripts/gen_catalog.py` to populate this table_

<!-- CATALOG:END -->
```

- [ ] **Step 3: Ignore Python build artifacts**

Write `.gitignore`:

```
__pycache__/
*.pyc
```

- [ ] **Step 4: Verify the plugin manifest is valid JSON**

Run: `python3 -m json.tool .claude-plugin/plugin.json`
Expected: pretty-printed JSON echoed back, no error.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json README.md .gitignore
git commit -m "Add plugin manifest and README skeleton"
```

---

### Task 2: Shared skill metadata module (`skill_meta.py`)

**Files:**
- Create: `skills/manage-skills/scripts/skill_meta.py`
- Test: `skills/manage-skills/scripts/tests/test_skill_meta.py`

- [ ] **Step 1: Write the failing tests**

Create `skills/manage-skills/scripts/tests/test_skill_meta.py`:

```python
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import skill_meta


class ParseKvBlockTests(unittest.TestCase):
    def test_parses_simple_pairs(self):
        text = "origin: mine\nsnapshotted_at: 2026-07-11\n"
        self.assertEqual(
            skill_meta.parse_kv_block(text),
            {"origin": "mine", "snapshotted_at": "2026-07-11"},
        )

    def test_preserves_urls_with_colons(self):
        text = "source_repo: https://github.com/flexprice/claude-plugin\n"
        self.assertEqual(
            skill_meta.parse_kv_block(text),
            {"source_repo": "https://github.com/flexprice/claude-plugin"},
        )

    def test_ignores_blank_lines_and_comments(self):
        text = "# comment\norigin: mine\n\nsource_repo: local\n"
        self.assertEqual(
            skill_meta.parse_kv_block(text),
            {"origin": "mine", "source_repo": "local"},
        )

    def test_empty_values_round_trip_not_dropped(self):
        text = "source_path:\nsource_ref: \n"
        self.assertEqual(
            skill_meta.parse_kv_block(text),
            {"source_path": "", "source_ref": ""},
        )


class OriginRoundTripTests(unittest.TestCase):
    def test_write_then_read_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "example-skill"
            skill_dir.mkdir()
            skill_meta.write_origin(skill_dir, {
                "origin": "vendored",
                "source_repo": "https://github.com/obra/superpowers",
                "source_path": "skills/brainstorming",
                "source_ref": "b557648",
                "snapshotted_at": "2026-07-11",
            })
            result = skill_meta.read_origin(skill_dir)
            self.assertEqual(result, {
                "origin": "vendored",
                "source_repo": "https://github.com/obra/superpowers",
                "source_path": "skills/brainstorming",
                "source_ref": "b557648",
                "snapshotted_at": "2026-07-11",
            })

    def test_write_origin_fills_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "example-skill"
            skill_dir.mkdir()
            skill_meta.write_origin(skill_dir, {
                "origin": "mine",
                "snapshotted_at": "2026-07-11",
            })
            result = skill_meta.read_origin(skill_dir)
            self.assertEqual(result["source_repo"], "local")
            self.assertEqual(result["source_path"], "")
            self.assertEqual(result["source_ref"], "")

    def test_empty_optional_fields_survive_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "example-skill"
            skill_dir.mkdir()
            skill_meta.write_origin(skill_dir, {
                "origin": "mine",
                "source_repo": "local",
                "source_path": "",
                "source_ref": "",
                "snapshotted_at": "2026-07-11",
            })
            result = skill_meta.read_origin(skill_dir)
            self.assertEqual(result["source_path"], "")
            self.assertEqual(result["source_ref"], "")


class ParseFrontmatterTests(unittest.TestCase):
    def test_parses_plain_value(self):
        text = "name: writing-plans\ndescription: Use when you have a spec.\n"
        self.assertEqual(
            skill_meta.parse_frontmatter(text),
            {"name": "writing-plans", "description": "Use when you have a spec."},
        )

    def test_strips_surrounding_quotes(self):
        text = 'name: brainstorming\ndescription: "Explore before building."\n'
        result = skill_meta.parse_frontmatter(text)
        self.assertEqual(result["description"], "Explore before building.")

    def test_joins_folded_block_scalar(self):
        text = (
            "name: pricing-setup\n"
            "description: >\n"
            "  Set up pricing by reading a pricing page.\n"
            "  Use this whenever the user wants to model pricing.\n"
        )
        result = skill_meta.parse_frontmatter(text)
        self.assertEqual(
            result["description"],
            "Set up pricing by reading a pricing page. "
            "Use this whenever the user wants to model pricing.",
        )

    def test_joins_literal_block_scalar_with_newlines(self):
        text = "name: example\ndescription: |\n  Line one.\n  Line two.\n"
        result = skill_meta.parse_frontmatter(text)
        self.assertEqual(result["description"], "Line one.\nLine two.")

    def test_captures_extra_fields(self):
        text = "name: graphify\ndescription: Turns things into graphs.\ntrigger: /graphify\n"
        result = skill_meta.parse_frontmatter(text)
        self.assertEqual(result["name"], "graphify")
        self.assertEqual(result["trigger"], "/graphify")


class ReadSkillFrontmatterTests(unittest.TestCase):
    def test_reads_frontmatter_from_skill_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "example-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: >\n  Does a thing\n  "
                "across two lines.\n---\n\n# Example\n"
            )
            result = skill_meta.read_skill_frontmatter(skill_dir)
            self.assertEqual(result["name"], "example-skill")
            self.assertEqual(result["description"], "Does a thing across two lines.")

    def test_raises_when_no_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "example-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# Example\nNo frontmatter here.\n")
            with self.assertRaises(ValueError):
                skill_meta.read_skill_frontmatter(skill_dir)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest discover -s skills/manage-skills/scripts/tests -p "test_skill_meta.py" -v`
Expected: ERROR — `ModuleNotFoundError: No module named 'skill_meta'` (the module doesn't exist yet).

- [ ] **Step 3: Implement `skill_meta.py`**

Create `skills/manage-skills/scripts/skill_meta.py`:

```python
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
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest discover -s skills/manage-skills/scripts/tests -p "test_skill_meta.py" -v`
Expected: `OK` with all tests listed as `ok` (16 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/manage-skills/scripts/skill_meta.py skills/manage-skills/scripts/tests/test_skill_meta.py
git commit -m "Add skill_meta module for .origin.yaml and SKILL.md frontmatter parsing"
```

---

### Task 3: Scaffolding script (`new_skill.py`)

**Files:**
- Create: `skills/manage-skills/scripts/new_skill.py`
- Test: `skills/manage-skills/scripts/tests/test_new_skill.py`

- [ ] **Step 1: Write the failing tests**

Create `skills/manage-skills/scripts/tests/test_new_skill.py`:

```python
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import new_skill
import skill_meta


class NewSkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.skills_dir = Path(self.tmp) / "skills"
        self.skills_dir.mkdir()

    def test_creates_stub_skill_with_origin(self):
        skill_dir = new_skill.new_skill(
            "example-skill", "mine", skills_dir=self.skills_dir,
        )
        self.assertTrue((skill_dir / "SKILL.md").exists())
        self.assertIn("TODO", (skill_dir / "SKILL.md").read_text())
        origin = skill_meta.read_origin(skill_dir)
        self.assertEqual(origin["origin"], "mine")
        self.assertEqual(origin["source_repo"], "local")

    def test_rejects_invalid_name(self):
        with self.assertRaises(ValueError):
            new_skill.new_skill("Bad Name!", "mine", skills_dir=self.skills_dir)

    def test_rejects_existing_skill(self):
        new_skill.new_skill("dup-skill", "mine", skills_dir=self.skills_dir)
        with self.assertRaises(FileExistsError):
            new_skill.new_skill("dup-skill", "mine", skills_dir=self.skills_dir)

    def test_seed_from_copies_real_content(self):
        seed_dir = Path(self.tmp) / "seed"
        seed_dir.mkdir()
        (seed_dir / "SKILL.md").write_text(
            "---\nname: seed\ndescription: Real content.\n---\n"
        )
        (seed_dir / "references").mkdir()
        (seed_dir / "references" / "notes.md").write_text("extra asset")

        skill_dir = new_skill.new_skill(
            "seeded-skill", "vendored", source_repo="local",
            seed_from=str(seed_dir), skills_dir=self.skills_dir,
        )
        self.assertIn("Real content.", (skill_dir / "SKILL.md").read_text())
        self.assertTrue((skill_dir / "references" / "notes.md").exists())

    def test_seed_from_requires_skill_md(self):
        seed_dir = Path(self.tmp) / "bad-seed"
        seed_dir.mkdir()
        with self.assertRaises(FileNotFoundError):
            new_skill.new_skill(
                "bad-skill", "vendored", seed_from=str(seed_dir),
                skills_dir=self.skills_dir,
            )

    def test_records_source_metadata(self):
        skill_dir = new_skill.new_skill(
            "tracked-skill", "vendored",
            source_repo="https://github.com/obra/superpowers",
            source_path="skills/brainstorming",
            source_ref="b557648",
            skills_dir=self.skills_dir,
        )
        origin = skill_meta.read_origin(skill_dir)
        self.assertEqual(origin["source_repo"], "https://github.com/obra/superpowers")
        self.assertEqual(origin["source_path"], "skills/brainstorming")
        self.assertEqual(origin["source_ref"], "b557648")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest discover -s skills/manage-skills/scripts/tests -p "test_new_skill.py" -v`
Expected: ERROR — `ModuleNotFoundError: No module named 'new_skill'`.

- [ ] **Step 3: Implement `new_skill.py`**

Create `skills/manage-skills/scripts/new_skill.py`:

```python
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
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest discover -s skills/manage-skills/scripts/tests -p "test_new_skill.py" -v`
Expected: `OK` with all 6 tests listed as `ok`.

- [ ] **Step 5: Commit**

```bash
git add skills/manage-skills/scripts/new_skill.py skills/manage-skills/scripts/tests/test_new_skill.py
git commit -m "Add new_skill.py scaffolding script"
```

---

### Task 4: Refresh script (`sync_skill.py`)

**Files:**
- Create: `skills/manage-skills/scripts/sync_skill.py`
- Test: `skills/manage-skills/scripts/tests/test_sync_skill.py`

- [ ] **Step 1: Write the failing tests**

Create `skills/manage-skills/scripts/tests/test_sync_skill.py`:

```python
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sync_skill
import skill_meta


class ResolveSourceDirTests(unittest.TestCase):
    def test_local_sentinel_returns_none(self):
        src, git_root = sync_skill.resolve_source_dir({"source_repo": "local"}, workdir="/tmp")
        self.assertIsNone(src)
        self.assertIsNone(git_root)

    def test_local_path_resolves_with_source_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "skills" / "example").mkdir(parents=True)
            src, git_root = sync_skill.resolve_source_dir(
                {"source_repo": str(repo), "source_path": "skills/example"},
                workdir=tmp,
            )
            self.assertEqual(src, repo / "skills" / "example")
            self.assertIsNone(git_root)

    def test_remote_url_triggers_clone(self):
        calls = []

        def fake_clone(url, dest):
            calls.append((url, dest))
            Path(dest).mkdir(parents=True)

        with tempfile.TemporaryDirectory() as tmp:
            src, git_root = sync_skill.resolve_source_dir(
                {"source_repo": "https://example.com/repo.git", "source_path": ""},
                workdir=tmp, clone=fake_clone,
            )
            self.assertEqual(len(calls), 1)
            self.assertEqual(src, git_root)

    def test_missing_local_path_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                sync_skill.resolve_source_dir(
                    {"source_repo": str(Path(tmp) / "does-not-exist")}, workdir=tmp,
                )


class SyncOneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_local_source_is_skipped(self):
        skill_dir = Path(self.tmp) / "skills" / "example"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: example\n---\n")
        skill_meta.write_origin(skill_dir, {
            "origin": "vendored", "source_repo": "local", "snapshotted_at": "2026-01-01",
        })
        changed = sync_skill.sync_one(skill_dir)
        self.assertFalse(changed)

    def test_copies_from_local_path_and_updates_snapshot(self):
        source_repo = Path(self.tmp) / "upstream"
        (source_repo / "skills" / "example").mkdir(parents=True)
        (source_repo / "skills" / "example" / "SKILL.md").write_text("new content")

        skill_dir = Path(self.tmp) / "skills" / "example"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("old content")
        skill_meta.write_origin(skill_dir, {
            "origin": "mine", "source_repo": str(source_repo),
            "source_path": "skills/example", "snapshotted_at": "2026-01-01",
        })

        changed = sync_skill.sync_one(skill_dir)
        self.assertTrue(changed)
        self.assertEqual((skill_dir / "SKILL.md").read_text(), "new content")
        origin = skill_meta.read_origin(skill_dir)
        self.assertNotEqual(origin["snapshotted_at"], "2026-01-01")

    def test_explicit_ref_overrides_detection(self):
        source_repo = Path(self.tmp) / "upstream2"
        (source_repo / "skills" / "example2").mkdir(parents=True)
        (source_repo / "skills" / "example2" / "SKILL.md").write_text("content")

        skill_dir = Path(self.tmp) / "skills" / "example2"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("content")
        skill_meta.write_origin(skill_dir, {
            "origin": "mine", "source_repo": str(source_repo),
            "source_path": "skills/example2", "snapshotted_at": "2026-01-01",
        })

        sync_skill.sync_one(skill_dir, new_ref="abc1234")
        origin = skill_meta.read_origin(skill_dir)
        self.assertEqual(origin["source_ref"], "abc1234")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest discover -s skills/manage-skills/scripts/tests -p "test_sync_skill.py" -v`
Expected: ERROR — `ModuleNotFoundError: No module named 'sync_skill'`.

- [ ] **Step 3: Implement `sync_skill.py`**

Create `skills/manage-skills/scripts/sync_skill.py`:

```python
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
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest discover -s skills/manage-skills/scripts/tests -p "test_sync_skill.py" -v`
Expected: `OK` with all 7 tests listed as `ok`.

- [ ] **Step 5: Commit**

```bash
git add skills/manage-skills/scripts/sync_skill.py skills/manage-skills/scripts/tests/test_sync_skill.py
git commit -m "Add sync_skill.py refresh script"
```

---

### Task 5: Catalog generator (`gen_catalog.py`)

**Files:**
- Create: `skills/manage-skills/scripts/gen_catalog.py`
- Test: `skills/manage-skills/scripts/tests/test_gen_catalog.py`

- [ ] **Step 1: Write the failing tests**

Create `skills/manage-skills/scripts/tests/test_gen_catalog.py`:

```python
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gen_catalog
import skill_meta


def make_skill(skills_dir, name, origin, description, source_repo="local"):
    skill_dir = Path(skills_dir) / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    )
    skill_meta.write_origin(skill_dir, {
        "origin": origin, "source_repo": source_repo, "snapshotted_at": "2026-01-01",
    })


class CollectSkillsTests(unittest.TestCase):
    def test_collects_frontmatter_and_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_skill(tmp, "alpha", "mine", "Does alpha things.")
            make_skill(tmp, "beta", "vendored", "Does beta things.",
                       source_repo="https://example.com/beta")
            rows = gen_catalog.collect_skills(tmp)
            names = {row["name"] for row in rows}
            self.assertEqual(names, {"alpha", "beta"})

    def test_skips_dirs_without_skill_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "not-a-skill").mkdir()
            rows = gen_catalog.collect_skills(tmp)
            self.assertEqual(rows, [])


class RenderTableTests(unittest.TestCase):
    def test_escapes_pipe_and_newline_in_description(self):
        rows = [{"name": "alpha", "description": "line one\nline two | three",
                 "source_repo": "local"}]
        table = gen_catalog.render_table(rows)
        self.assertNotIn("\n\n", table)
        self.assertIn("line one line two \\| three", table)


class RenderCatalogTests(unittest.TestCase):
    def test_groups_by_origin(self):
        rows = [
            {"name": "alpha", "description": "d1", "origin": "mine", "source_repo": "local"},
            {"name": "beta", "description": "d2", "origin": "vendored", "source_repo": "local"},
        ]
        catalog = gen_catalog.render_catalog(rows)
        self.assertIn("### Mine", catalog)
        self.assertIn("alpha", catalog)
        self.assertIn("### Vendored", catalog)
        self.assertIn("beta", catalog)
        self.assertLess(catalog.index("alpha"), catalog.index("beta"))


class UpdateReadmeTests(unittest.TestCase):
    def test_replaces_only_marked_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            make_skill(skills_dir, "alpha", "mine", "Does alpha things.")

            readme_path = Path(tmp) / "README.md"
            readme_path.write_text(
                "# Title\n\nIntro text.\n\n<!-- CATALOG:START -->\nold\n"
                "<!-- CATALOG:END -->\n\nFooter.\n"
            )
            new_text = gen_catalog.update_readme(readme_path, skills_dir)
            self.assertIn("Intro text.", new_text)
            self.assertIn("Footer.", new_text)
            self.assertIn("alpha", new_text)
            self.assertNotIn("old", new_text)

    def test_raises_without_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            readme_path = Path(tmp) / "README.md"
            readme_path.write_text("# Title\nNo markers here.\n")
            with self.assertRaises(ValueError):
                gen_catalog.update_readme(readme_path, skills_dir)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest discover -s skills/manage-skills/scripts/tests -p "test_gen_catalog.py" -v`
Expected: ERROR — `ModuleNotFoundError: No module named 'gen_catalog'`.

- [ ] **Step 3: Implement `gen_catalog.py`**

Create `skills/manage-skills/scripts/gen_catalog.py`:

```python
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
```

Note: `root` here is `skills/manage-skills/scripts/../../` = `skills/`; `root.parent` is the repo root, so `root.parent / "README.md"` is correct.

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest discover -s skills/manage-skills/scripts/tests -p "test_gen_catalog.py" -v`
Expected: `OK` with all 6 tests listed as `ok`.

- [ ] **Step 5: Commit**

```bash
git add skills/manage-skills/scripts/gen_catalog.py skills/manage-skills/scripts/tests/test_gen_catalog.py
git commit -m "Add gen_catalog.py README catalog generator"
```

---

### Task 6: The `manage-skills` skill itself

**Files:**
- Create: `skills/manage-skills/SKILL.md`
- Create: `skills/manage-skills/.origin.yaml`

- [ ] **Step 1: Write `SKILL.md`**

Create `skills/manage-skills/SKILL.md`:

```markdown
---
name: manage-skills
description: Use when adding a new skill to this repo, refreshing a vendored or mine skill from its source, or regenerating the skill catalog in README.md.
---

# Managing This Skills Repo

This repo holds two kinds of skills under `skills/`, distinguished by each skill's `.origin.yaml`, not by folder location (the directory stays flat so the repo works as an installable Claude Code plugin):

- **mine** — skills authored directly in this repo, or snapshotted from a repo the user owns.
- **vendored** — third-party skills snapshotted in for reference and use.

Three scripts under `scripts/` handle the mechanical parts. Run them from the repo root.

## Add a new skill

```
python3 skills/manage-skills/scripts/new_skill.py <name> --origin mine|vendored \
  [--source-repo REPO] [--source-path PATH] [--source-ref REF] [--seed-from DIR]
```

- Without `--seed-from`: scaffolds `skills/<name>/SKILL.md` as a TODO stub — use this for a skill you're about to write from scratch.
- With `--seed-from DIR`: copies `DIR`'s full contents (it must already contain a `SKILL.md`) into `skills/<name>/` — use this to adopt an existing skill, whether one you wrote elsewhere or a third-party one you're vendoring in.
- `--source-repo` defaults to `local`, meaning "no separate repo tracks this content" (nothing to sync from later). Set it to a git URL or a local path to an existing checkout when there IS a canonical upstream, so `sync_skill.py` can refresh from it later.

After adding a skill, run `gen_catalog.py` (below) to refresh `README.md`.

## Refresh a skill from its source

```
python3 skills/manage-skills/scripts/sync_skill.py <name>
python3 skills/manage-skills/scripts/sync_skill.py --all
```

Reads the skill's `.origin.yaml`. If `source_repo` is `local`, there's nothing to sync (this repo IS the only copy) and the script says so and exits. Otherwise it re-copies from the recorded local path, or shallow-clones the recorded URL into a scratch directory first, then updates `source_ref`/`snapshotted_at`.

## Regenerate the catalog

```
python3 skills/manage-skills/scripts/gen_catalog.py
```

Rebuilds the table between the `<!-- CATALOG:START -->`/`<!-- CATALOG:END -->` markers in `README.md` from every skill's `SKILL.md` frontmatter and `.origin.yaml`. Safe to run any time; never edit that table by hand since it will be overwritten.

## Writing or improving a skill's content

This skill only handles repo mechanics (scaffolding, syncing, cataloging). For guidance on structuring a skill well — tight descriptions, when to trigger, avoiding bloat — use the vendored `writing-skills` skill instead of duplicating that guidance here.
```

- [ ] **Step 2: Write `.origin.yaml`**

Create `skills/manage-skills/.origin.yaml`:

```
origin: mine
source_repo: local
source_path:
source_ref:
snapshotted_at: 2026-07-11
```

- [ ] **Step 3: Verify every script's `--help` matches what `SKILL.md` documents**

Run:
```bash
python3 skills/manage-skills/scripts/new_skill.py --help
python3 skills/manage-skills/scripts/sync_skill.py --help
python3 skills/manage-skills/scripts/gen_catalog.py --help
```
Expected: each prints its usage/argument list without error (`gen_catalog.py --help` shows just the description, since it takes no arguments); confirm the flags shown match those documented in `SKILL.md`.

- [ ] **Step 4: Commit**

```bash
git add skills/manage-skills/SKILL.md skills/manage-skills/.origin.yaml
git commit -m "Add manage-skills SKILL.md and origin metadata"
```

---

### Task 7: Migrate "mine" skills (Flexprice)

**Files:**
- Create: `skills/pricing-setup/`, `skills/subscription-import/`, `skills/batch-subscription-draft-compute/`, `skills/batch-invoice-compute/`, `skills/invoice-validation/`, `skills/draft-invoice-recalculate/` (each via `new_skill.py --seed-from`)

- [ ] **Step 1: Scaffold and seed all 6 skills**

Run each of the following from the repo root:

```bash
python3 skills/manage-skills/scripts/new_skill.py pricing-setup \
  --origin mine \
  --source-repo https://github.com/flexprice/claude-plugin \
  --source-path skills/pricing-setup \
  --source-ref c4cd3f7 \
  --seed-from /Users/omkar/Developer/source-code/flexprice/flexprice-claude-plugin/skills/pricing-setup

python3 skills/manage-skills/scripts/new_skill.py subscription-import \
  --origin mine \
  --source-repo https://github.com/flexprice/claude-plugin \
  --source-path skills/subscription-import \
  --source-ref c4cd3f7 \
  --seed-from /Users/omkar/Developer/source-code/flexprice/flexprice-claude-plugin/skills/subscription-import

python3 skills/manage-skills/scripts/new_skill.py batch-subscription-draft-compute \
  --origin mine \
  --source-repo https://github.com/flexprice/claude-plugin \
  --source-path skills/batch-subscription-draft-compute \
  --source-ref c4cd3f7 \
  --seed-from /Users/omkar/Developer/source-code/flexprice/flexprice-claude-plugin/skills/batch-subscription-draft-compute

python3 skills/manage-skills/scripts/new_skill.py batch-invoice-compute \
  --origin mine \
  --source-repo https://github.com/flexprice/claude-plugin \
  --source-path skills/batch-invoice-compute \
  --source-ref c4cd3f7 \
  --seed-from /Users/omkar/Developer/source-code/flexprice/flexprice-claude-plugin/skills/batch-invoice-compute

python3 skills/manage-skills/scripts/new_skill.py invoice-validation \
  --origin mine \
  --source-repo https://github.com/flexprice/claude-plugin \
  --source-path skills/invoice-validation \
  --source-ref c4cd3f7 \
  --seed-from /Users/omkar/Developer/source-code/flexprice/flexprice-claude-plugin/skills/invoice-validation

python3 skills/manage-skills/scripts/new_skill.py draft-invoice-recalculate \
  --origin mine \
  --source-repo https://github.com/flexprice/claude-plugin \
  --source-path skills/draft-invoice-recalculate \
  --source-ref c4cd3f7 \
  --seed-from /Users/omkar/Developer/source-code/flexprice/flexprice-claude-plugin/skills/draft-invoice-recalculate
```

Expected: each prints `Created .../skills/<name>` followed by the catalog reminder.

- [ ] **Step 2: Verify**

Run: `ls skills/ && cat skills/pricing-setup/.origin.yaml`
Expected: all 6 directories listed; the `.origin.yaml` shows `origin: mine`, `source_repo: https://github.com/flexprice/claude-plugin`, `source_ref: c4cd3f7`.

- [ ] **Step 3: Commit**

```bash
git add skills/pricing-setup skills/subscription-import skills/batch-subscription-draft-compute \
  skills/batch-invoice-compute skills/invoice-validation skills/draft-invoice-recalculate
git commit -m "Migrate mine skills from flexprice-claude-plugin"
```

---

### Task 8: Migrate vendored superpowers skills

**Files:**
- Create: `skills/brainstorming/`, `skills/writing-plans/`, `skills/executing-plans/`, `skills/systematic-debugging/`, `skills/test-driven-development/`, `skills/requesting-code-review/`, `skills/receiving-code-review/`, `skills/writing-skills/` (each via `new_skill.py --seed-from`)

- [ ] **Step 1: Scaffold and seed all 8 skills**

Run each of the following from the repo root:

```bash
python3 skills/manage-skills/scripts/new_skill.py brainstorming \
  --origin vendored \
  --source-repo https://github.com/obra/superpowers \
  --source-path skills/brainstorming \
  --source-ref b557648 \
  --seed-from /Users/omkar/.claude/plugins/marketplaces/superpowers-dev/skills/brainstorming

python3 skills/manage-skills/scripts/new_skill.py writing-plans \
  --origin vendored \
  --source-repo https://github.com/obra/superpowers \
  --source-path skills/writing-plans \
  --source-ref b557648 \
  --seed-from /Users/omkar/.claude/plugins/marketplaces/superpowers-dev/skills/writing-plans

python3 skills/manage-skills/scripts/new_skill.py executing-plans \
  --origin vendored \
  --source-repo https://github.com/obra/superpowers \
  --source-path skills/executing-plans \
  --source-ref b557648 \
  --seed-from /Users/omkar/.claude/plugins/marketplaces/superpowers-dev/skills/executing-plans

python3 skills/manage-skills/scripts/new_skill.py systematic-debugging \
  --origin vendored \
  --source-repo https://github.com/obra/superpowers \
  --source-path skills/systematic-debugging \
  --source-ref b557648 \
  --seed-from /Users/omkar/.claude/plugins/marketplaces/superpowers-dev/skills/systematic-debugging

python3 skills/manage-skills/scripts/new_skill.py test-driven-development \
  --origin vendored \
  --source-repo https://github.com/obra/superpowers \
  --source-path skills/test-driven-development \
  --source-ref b557648 \
  --seed-from /Users/omkar/.claude/plugins/marketplaces/superpowers-dev/skills/test-driven-development

python3 skills/manage-skills/scripts/new_skill.py requesting-code-review \
  --origin vendored \
  --source-repo https://github.com/obra/superpowers \
  --source-path skills/requesting-code-review \
  --source-ref b557648 \
  --seed-from /Users/omkar/.claude/plugins/marketplaces/superpowers-dev/skills/requesting-code-review

python3 skills/manage-skills/scripts/new_skill.py receiving-code-review \
  --origin vendored \
  --source-repo https://github.com/obra/superpowers \
  --source-path skills/receiving-code-review \
  --source-ref b557648 \
  --seed-from /Users/omkar/.claude/plugins/marketplaces/superpowers-dev/skills/receiving-code-review

python3 skills/manage-skills/scripts/new_skill.py writing-skills \
  --origin vendored \
  --source-repo https://github.com/obra/superpowers \
  --source-path skills/writing-skills \
  --source-ref b557648 \
  --seed-from /Users/omkar/.claude/plugins/marketplaces/superpowers-dev/skills/writing-skills
```

Expected: each prints `Created .../skills/<name>` followed by the catalog reminder.

- [ ] **Step 2: Verify**

Run: `ls skills/ && cat skills/brainstorming/.origin.yaml`
Expected: all 8 new directories listed alongside the mine skills from Task 7; `.origin.yaml` shows `origin: vendored`, `source_repo: https://github.com/obra/superpowers`, `source_ref: b557648`.

- [ ] **Step 3: Commit**

```bash
git add skills/brainstorming skills/writing-plans skills/executing-plans skills/systematic-debugging \
  skills/test-driven-development skills/requesting-code-review skills/receiving-code-review skills/writing-skills
git commit -m "Vendor superpowers core workflow skills"
```

---

### Task 9: Migrate vendored design skills and graphify

**Files:**
- Create: `skills/frontend-design/`, `skills/ui-ux-pro-max/`, `skills/graphify/` (each via `new_skill.py --seed-from`)

- [ ] **Step 1: Scaffold and seed all 3 skills**

Run each of the following from the repo root:

```bash
python3 skills/manage-skills/scripts/new_skill.py frontend-design \
  --origin vendored \
  --source-repo local \
  --seed-from /Users/omkar/.claude/skills/frontend-design

python3 skills/manage-skills/scripts/new_skill.py ui-ux-pro-max \
  --origin vendored \
  --source-repo local \
  --seed-from /Users/omkar/.claude/skills/ui-ux-pro-max

python3 skills/manage-skills/scripts/new_skill.py graphify \
  --origin vendored \
  --source-repo local \
  --source-ref 0.8.14 \
  --seed-from /Users/omkar/.claude/skills/graphify
```

Expected: each prints `Created .../skills/<name>` followed by the catalog reminder.

- [ ] **Step 2: Verify**

Run: `ls skills/ && cat skills/graphify/.origin.yaml`
Expected: all 3 new directories listed; `.origin.yaml` for `graphify` shows `origin: vendored`, `source_repo: local`, `source_ref: 0.8.14`.

- [ ] **Step 3: Commit**

```bash
git add skills/frontend-design skills/ui-ux-pro-max skills/graphify
git commit -m "Vendor local design skills and graphify"
```

---

### Task 10: Regenerate the catalog and final verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Regenerate the catalog**

Run: `python3 skills/manage-skills/scripts/gen_catalog.py`
Expected: prints `README.md catalog regenerated`.

- [ ] **Step 2: Verify the Flexprice folded descriptions rendered correctly**

Run: `grep -A2 'pricing-setup' README.md`
Expected: the `pricing-setup` row shows a single-line description starting with "Set up FlexPrice features, plans, and usage-based pricing..." (not truncated to `>`, not split across broken table rows).

- [ ] **Step 3: Verify all 18 skills are cataloged**

Run: `grep -c '^| \`' README.md`
Expected: `18` (the 6 mine + 8 superpowers + 3 design/graphify skills from Tasks 7–9, plus `manage-skills` itself from Task 6).

- [ ] **Step 4: Run the full test suite once more**

Run: `python3 -m unittest discover -s skills/manage-skills/scripts/tests -v`
Expected: `OK` with all tests from Tasks 2, 4, and 5 passing (test_new_skill.py's tests also run and pass).

- [ ] **Step 5: Verify the plugin manifest still parses**

Run: `python3 -m json.tool .claude-plugin/plugin.json`
Expected: pretty-printed JSON, no error.

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "Regenerate skill catalog with all migrated skills"
```

---

## Plan self-review notes

- **Spec coverage:** flat plugin-compatible `skills/` layout (Task 1), `.origin.yaml` schema (Task 2), plugin scaffolding (Task 1), `manage-skills` with scaffold/sync/catalog (Tasks 3–6), all 4 categories of initial migration (Tasks 7–9), generated README catalog (Task 5, 10) — all covered.
- **Known limitation to carry forward, not fixed here (YAGNI):** `parse_frontmatter` handles the frontmatter styles actually present in this migration (plain, quoted, `>`/`|` block scalars). It is not a general YAML parser — a skill with a YAML list or nested mapping in its frontmatter would need the parser extended when that actually comes up.
