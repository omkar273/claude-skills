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
