"""Run the Cline extension installer against temporary home directories."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/install_cline.py"


class InstallClineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vibe-wise-cline-home-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def install(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--home", str(self.home)],
            text=True, capture_output=True, timeout=30,
        )

    def test_installs_skills_and_always_on_rule(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("learn", "reset"):
            installed = self.home / ".cline/skills" / name
            self.assertEqual(
                sorted(p.name for p in installed.iterdir()),
                sorted(p.name for p in (ROOT / "skills" / name).iterdir()),
            )
        rule = (self.home / "Documents/Cline/Rules/vibe-wise.md").read_text(encoding="utf-8")
        # Cline treats frontmatter as conditions; a rule without it is always active.
        self.assertFalse(rule.startswith("---"))
        self.assertIn("Learning mode: paused", rule)
        self.assertIn("load the `learn` skill", rule)

    def test_reinstall_replaces_previous_copy(self):
        self.assertEqual(self.install().returncode, 0)
        stale = self.home / ".cline/skills/learn/stale.md"
        stale.write_text("old")
        self.assertEqual(self.install().returncode, 0)
        self.assertFalse(stale.exists())

    def test_refuses_to_replace_someone_elses_skill(self):
        foreign = self.home / ".cline/skills/learn"
        foreign.mkdir(parents=True)
        (foreign / "SKILL.md").write_text("---\nname: learn\n---\nA different skill.\n")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("isn't a VibeWise skill", result.stderr)
        self.assertEqual((foreign / "SKILL.md").read_text(), "---\nname: learn\n---\nA different skill.\n")
        self.assertFalse((self.home / "Documents/Cline/Rules/vibe-wise.md").exists())


if __name__ == "__main__":
    unittest.main()
