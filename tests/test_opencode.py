"""Run the OpenCode plugin under Bun with a minimal fake host."""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "adapters/opencode/plugin.ts"
BUN = shutil.which("bun") or str(Path.home() / ".bun/bin/bun")

# The fake client answers session.get with the directory registered for that
# session, like OpenCode does for sessions started in different directories.
RUNNER = """
import { VibeWise } from %s;
const input = JSON.parse(await Bun.stdin.text());
const client = { session: { get: async ({ path }) => ({ data: { directory: input.sessions[path.id] } }) } };
const hooks = await VibeWise({ client, directory: input.directory });
const config = input.config;
await hooks.config(config);
const systems = {};
for (const id of Object.keys(input.sessions)) {
  const output = { system: [] };
  await hooks["experimental.chat.system.transform"]({ sessionID: id, model: {} }, output);
  systems[id] = output.system;
}
console.log(JSON.stringify({ config, systems }));
""" % json.dumps(str(PLUGIN_PATH))


@unittest.skipUnless(Path(BUN).exists(), "bun is required to run the OpenCode plugin")
class OpenCodePluginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vibe-wise-opencode-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "runner.ts").write_text(RUNNER)

    def project(self, name, mode=None):
        project = self.root / name
        (project / ".git").mkdir(parents=True)
        if mode:
            state = project / ".vibe-wise"
            state.mkdir()
            (state / "profile.md").write_text(f"Learning mode: {mode}\nPRIVATE NOTE\n")
        return project

    def run_plugin(self, sessions, config=None):
        result = subprocess.run(
            [BUN, str(self.root / "runner.ts")],
            input=json.dumps({"directory": str(self.root), "sessions": sessions,
                              "config": config if config is not None else {}}),
            text=True, capture_output=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_each_session_restores_from_its_own_directory(self):
        active = self.project("active", "active")
        paused = self.project("paused", "paused")
        fresh = self.project("fresh")
        systems = self.run_plugin({"a": str(active), "p": str(paused), "f": str(fresh)})["systems"]
        self.assertEqual(len(systems["a"]), 1)
        self.assertIn(str(ROOT / "skills/learn/SKILL.md"), systems["a"][0])
        self.assertIn(str(active / ".vibe-wise"), systems["a"][0])
        self.assertNotIn("PRIVATE NOTE", systems["a"][0])
        self.assertEqual(systems["p"], [])
        self.assertEqual(systems["f"], [])

    def test_registers_commands_that_point_at_the_guides(self):
        commands = self.run_plugin({})["config"]["command"]
        self.assertEqual(sorted(commands), ["vibe-wise-learn", "vibe-wise-reset"])
        self.assertIn(str(ROOT / "skills/learn/SKILL.md"), commands["vibe-wise-learn"]["template"])
        self.assertIn(str(ROOT / "skills/reset/SKILL.md"), commands["vibe-wise-reset"]["template"])
        self.assertIn("$ARGUMENTS", commands["vibe-wise-learn"]["template"])

    def test_user_command_with_the_same_name_wins(self):
        config = {"command": {"vibe-wise-learn": {"template": "mine"}}}
        commands = self.run_plugin({}, config)["config"]["command"]
        self.assertEqual(commands["vibe-wise-learn"], {"template": "mine"})

    def test_allows_only_the_guides_outside_the_project(self):
        skills = str(ROOT / "skills" / "**")
        cases = [
            ({}, {"*": "ask", skills: "allow"}),
            ({"permission": {"external_directory": "allow"}}, {"*": "allow", skills: "allow"}),
            ({"permission": {"external_directory": {"~/x/**": "allow"}}},
             {"~/x/**": "allow", skills: "allow"}),
            # An explicit global deny is the user's decision; don't punch a hole in it.
            ({"permission": {"external_directory": "deny"}}, "deny"),
        ]
        for config, expected in cases:
            with self.subTest(config=config):
                result = self.run_plugin({}, config)["config"]["permission"]
                self.assertEqual(result["external_directory"], expected)


if __name__ == "__main__":
    unittest.main()
