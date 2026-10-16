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

    def install(self, *extra):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--home", str(self.home), *extra],
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_commands_and_rule_point_at_the_copied_guides(self):
        self.install()
        guides = self.home / ".cline/vibe-wise"
        for name in ("learn", "reset"):
            self.assertEqual(
                sorted(p.name for p in (guides / name).iterdir()),
                sorted(p.name for p in (ROOT / "skills" / name).iterdir()),
            )
        workflows = self.home / "Documents/Cline/Workflows"
        self.assertEqual(sorted(p.name for p in workflows.iterdir()),
                         ["vibe-wise-learn", "vibe-wise-reset"])
        self.assertIn(str(guides / "learn/SKILL.md"), (workflows / "vibe-wise-learn").read_text())
        self.assertIn(str(guides / "reset/SKILL.md"), (workflows / "vibe-wise-reset").read_text())
        rule = (self.home / "Documents/Cline/Rules/vibe-wise.md").read_text()
        # Cline treats frontmatter as conditions; a rule without it is always active.
        self.assertFalse(rule.startswith("---"))
        self.assertIn("Learning mode: paused", rule)
        self.assertIn(str(guides / "learn/SKILL.md"), rule)
        self.assertNotIn("`learn` skill", rule)

    def test_nothing_is_installed_as_a_cline_skill(self):
        # Cline offers every skill to the model and ignores disable-model-invocation,
        # so a skill could start onboarding unasked.
        self.install()
        self.assertFalse((self.home / ".cline/skills").exists())

    def test_removes_skills_from_earlier_versions_but_not_other_skills(self):
        old = self.home / ".cline/skills/learn"
        old.mkdir(parents=True)
        (old / "SKILL.md").write_text("# VibeWise Learn mode\n")
        mine = self.home / ".cline/skills/reset"
        mine.mkdir(parents=True)
        (mine / "SKILL.md").write_text("A different reset skill.\n")
        self.install()
        self.assertFalse(old.exists())
        self.assertEqual((mine / "SKILL.md").read_text(), "A different reset skill.\n")

    def test_reinstall_replaces_previous_guides(self):
        self.install()
        stale = self.home / ".cline/vibe-wise/learn/stale.md"
        stale.write_text("old")
        self.install()
        self.assertFalse(stale.exists())

    def test_documents_override_moves_rule_and_workflows_only(self):
        # Under WSL, Cline's Documents folder is xdg-user-dir's answer, often $HOME.
        self.install("--documents", str(self.home))
        self.assertTrue((self.home / "Cline/Rules/vibe-wise.md").is_file())
        self.assertTrue((self.home / "Cline/Workflows/vibe-wise-learn").is_file())
        self.assertFalse((self.home / "Documents").exists())

    def test_windows_home_from_wsl_uses_drive_letter_paths(self):
        sys.path.insert(0, str(SCRIPT.parent))
        self.addCleanup(sys.path.remove, str(SCRIPT.parent))
        from install_cline import as_seen_by_cline
        self.assertEqual(
            as_seen_by_cline(Path("/mnt/c/Users/me/.cline/vibe-wise/learn/SKILL.md")),
            r"C:\Users\me\.cline\vibe-wise\learn\SKILL.md",
        )
        self.assertEqual(as_seen_by_cline(Path("/home/me/x")), "/home/me/x")


if __name__ == "__main__":
    unittest.main()
