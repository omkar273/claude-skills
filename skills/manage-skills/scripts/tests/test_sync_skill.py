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
