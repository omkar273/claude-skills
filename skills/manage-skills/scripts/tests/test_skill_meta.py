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
