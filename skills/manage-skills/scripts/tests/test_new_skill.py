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
