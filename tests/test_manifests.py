"""Keep every host's manifest on the release version Claude Code's manifest declares."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Upstream bumps .claude-plugin/plugin.json on each release; the other hosts' manifests
# must follow, or Copilot/omp/Cline/OpenCode installs report a stale version.
MANIFESTS = ("plugin.json", "package.json", ".codex-plugin/plugin.json")


class ManifestVersionTests(unittest.TestCase):
    def test_all_manifests_share_the_release_version(self):
        release = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())["version"]
        for name in MANIFESTS:
            with self.subTest(manifest=name):
                self.assertEqual(json.loads((ROOT / name).read_text())["version"], release)


if __name__ == "__main__":
    unittest.main()
