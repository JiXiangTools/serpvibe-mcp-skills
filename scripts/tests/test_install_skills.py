import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "install_skills", ROOT / "scripts/install_skills.py"
)
INSTALLER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(INSTALLER)


class InstallSkillsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="serpvibe-skills-")
        self.addCleanup(temporary.cleanup)
        self.destination = Path(temporary.name).resolve() / "skills"

    def test_default_install_is_one_operation_and_excludes_independent_skill(self):
        installed, unchanged = INSTALLER.install(
            list(INSTALLER.DEFAULT_SKILLS), self.destination
        )
        self.assertEqual(installed, list(INSTALLER.DEFAULT_SKILLS))
        self.assertEqual(unchanged, [])
        self.assertEqual(
            sorted(path.name for path in self.destination.iterdir()),
            sorted(INSTALLER.DEFAULT_SKILLS),
        )
        self.assertFalse((self.destination / "browser-env-manager").exists())

    def test_identical_install_is_idempotent(self):
        INSTALLER.install(list(INSTALLER.DEFAULT_SKILLS), self.destination)
        installed, unchanged = INSTALLER.install(
            list(INSTALLER.DEFAULT_SKILLS), self.destination
        )
        self.assertEqual(installed, [])
        self.assertEqual(unchanged, list(INSTALLER.DEFAULT_SKILLS))

    def test_changed_existing_skill_is_preserved(self):
        target = self.destination / "account-management"
        target.mkdir(parents=True)
        marker = target / "user-file"
        marker.write_text("keep")
        with self.assertRaisesRegex(INSTALLER.InstallError, "refusing to overwrite"):
            INSTALLER.install(["account-management"], self.destination)
        self.assertEqual(marker.read_text(), "keep")

    def test_symlinked_skill_is_preserved(self):
        source = self.destination.parent / "managed-elsewhere"
        source.mkdir(parents=True)
        self.destination.mkdir()
        target = self.destination / "account-management"
        target.symlink_to(source, target_is_directory=True)
        with self.assertRaisesRegex(INSTALLER.InstallError, "symlinked"):
            INSTALLER.install(["account-management"], self.destination)
        self.assertTrue(target.is_symlink())


if __name__ == "__main__":
    unittest.main()
