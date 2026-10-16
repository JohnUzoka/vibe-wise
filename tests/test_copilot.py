"""Contract and integration tests for GitHub Copilot CLI support."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOOKS_CONFIG_PATH = ROOT / "com.github.copilot/hooks/hooks.json"
RULES_DIR = ROOT / "com.github.copilot/rules"
PLUGIN_MANIFEST_PATH = ROOT / "plugin.json"
MARKETPLACE_MANIFEST_PATH = ROOT / ".github/plugin/marketplace.json"


class CopilotRegistrationSchemaTests(unittest.TestCase):
    """Validate that Copilot configuration and manifest files conform to the documented schema."""

    def test_hooks_registration_schema(self):
        self.assertTrue(HOOKS_CONFIG_PATH.is_file(), "hooks.json must exist")
        config = json.loads(HOOKS_CONFIG_PATH.read_text(encoding="utf-8"))

        self.assertEqual(config.get("version"), 1, "Hooks config must declare version 1")
        self.assertIn("hooks", config, "Hooks config must contain 'hooks' mapping")

        hooks = config["hooks"]
        self.assertIn("sessionStart", hooks, "Hooks must register sessionStart event")
        self.assertIsInstance(hooks["sessionStart"], list, "sessionStart entries must be an array")
        self.assertGreater(len(hooks["sessionStart"]), 0, "sessionStart must have at least one hook")

        entry = hooks["sessionStart"][0]
        self.assertEqual(entry.get("type"), "command", "Hook type must be 'command'")
        self.assertIn("bash", entry, "Hook must define 'bash' command")
        self.assertIn("powershell", entry, "Hook must define 'powershell' command")
        self.assertEqual(entry.get("timeoutSec"), 5, "Hook timeoutSec must be 5 seconds")

        self.assertIn("--host copilot", entry["bash"])
        self.assertIn("${PLUGIN_ROOT}", entry["bash"])
        self.assertIn("--host copilot", entry["powershell"])
        self.assertIn("${PLUGIN_ROOT}", entry["powershell"])

    def test_manifest_opts_into_agent_plugins(self):
        # Copilot reads com.github.copilot/ (hooks, rules) only for Agent Plugins
        # manifests; a legacy manifest would silently drop the rule and the hook.
        manifest = json.loads(PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("$schema"),
                         "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        self.assertEqual(manifest.get("name"), "vibe-wise")
        self.assertFalse({"skills", "hooks"} & manifest.keys(),
                         "component paths are fixed in Agent Plugins manifests")
        self.assertFalse((ROOT / ".github/plugin/plugin.json").exists(),
                         "a second manifest would compete with the root one")

    def test_rule_is_always_applied_and_loadable(self):
        # Copilot 1.0.98 loads plugin rules only as .mdc files (a .md file was
        # ignored by `copilot instruction list`) and requires a description.
        rules = sorted(RULES_DIR.iterdir())
        self.assertEqual([p.name for p in rules], ["vibe-wise.mdc"])
        text = rules[0].read_text(encoding="utf-8")
        front = text.split("---")[1]
        self.assertRegex(front, r"(?m)^description: \S")
        self.assertRegex(front, r"(?m)^alwaysApply: true$")
        # The rule is always loaded, so it must defer to the profile to stay
        # silent in projects that never ran Learn or that paused it.
        self.assertIn("Learning mode: paused", text)
        self.assertIn("ignore this rule", text)

    def test_marketplace_manifest_schema(self):
        self.assertTrue(MARKETPLACE_MANIFEST_PATH.is_file(), "marketplace.json must exist")
        marketplace = json.loads(MARKETPLACE_MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertEqual(marketplace.get("name"), "vibe-wise")
        self.assertIn("plugins", marketplace)
        self.assertIsInstance(marketplace["plugins"], list)

        plugin_entries = [p for p in marketplace["plugins"] if p.get("name") == "vibe-wise"]
        self.assertEqual(len(plugin_entries), 1)
        self.assertEqual(plugin_entries[0].get("source"), "./")


class CopilotHookExecutionTests(unittest.TestCase):
    """Execute the registered Copilot command with real JSON payloads in temp projects."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vibe-wise-copilot-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "copilot project"
        self.project.mkdir()
        (self.project / ".git").mkdir()

        config = json.loads(HOOKS_CONFIG_PATH.read_text(encoding="utf-8"))
        raw_cmd = config["hooks"]["sessionStart"][0]["bash"]
        # Expand ${PLUGIN_ROOT} as Copilot CLI does when dispatching plugin command hooks
        self.command = raw_cmd.replace("${PLUGIN_ROOT}", str(ROOT))

    def create_state(self, project=None, mode="active"):
        directory = (project or self.project) / ".vibe-wise"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "profile.md").write_text(
            f"# Learner Profile\nLearning mode: {mode}\nOnboarding: complete\n"
            "Checkpoint frequency: Light\nQuestion style: Open-ended\n"
            "Implementation style: AI writes code\n"
            "Strong concepts: Asynchronous I/O\n", encoding="utf-8"
        )
        (directory / "project-map.md").write_text(
            "# Project Map\nmain.py → api.py → database.py\n", encoding="utf-8"
        )
        (directory / "progress.md").write_text(
            "# Learning Progress\n## Async Tasks\n"
            "Demonstrated understanding: event loop primitives.\n"
            "## Database Pooling\nNeeds reinforcement: pool exhaustion.\n", encoding="utf-8"
        )
        return directory

    def run_hook(self, payload):
        input_data = json.dumps(payload) if isinstance(payload, dict) else payload
        result = subprocess.run(
            self.command, shell=True,
            input=input_data, text=True, capture_output=True, timeout=5,
            env={
                "PATH": os.pathsep.join((str(Path(sys.executable).parent), os.defpath)),
                "PLUGIN_ROOT": str(ROOT),
                "COPILOT_PLUGIN_ROOT": str(ROOT),
            }, cwd=str(self.root),
        )
        self.assertEqual(result.returncode, 0, f"Hook failed with error: {result.stderr}")
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout) if result.stdout.strip() else None

    def test_fresh_project_without_state_produces_no_output(self):
        for source in ("startup", "resume", "new"):
            with self.subTest(source=source):
                payload = {
                    "sessionId": "sess-fresh-1",
                    "cwd": str(self.project),
                    "source": source,
                    "timestamp": 1729000000000,
                }
                self.assertIsNone(self.run_hook(payload))

    def test_paused_profile_produces_no_output(self):
        self.create_state(mode="paused")
        for source in ("startup", "resume", "new"):
            with self.subTest(source=source):
                payload = {
                    "sessionId": "sess-paused-1",
                    "cwd": str(self.project),
                    "source": source,
                    "timestamp": 1729000000000,
                }
                self.assertIsNone(self.run_hook(payload))

    def test_active_profile_camelcase_format_all_sources(self):
        state_dir = self.create_state(mode="active")
        for source in ("startup", "resume", "new"):
            with self.subTest(source=source):
                payload = {
                    "sessionId": f"sess-active-{source}",
                    "cwd": str(self.project),
                    "source": source,
                    "timestamp": 1729000000000,
                }
                result = self.run_hook(payload)
                self.assertIsNotNone(result)
                self.assertIn("additionalContext", result)

                context = result["additionalContext"]
                # Must point to SKILL.md and state directory
                self.assertIn(str(ROOT / "skills/learn/SKILL.md"), context)
                self.assertIn(str(state_dir), context)
                self.assertIn("Read profile.md and project-map.md", context)
                self.assertIn("Search the entire progress.md", context)

                # Must not contain private learner note contents
                self.assertNotIn("Checkpoint frequency: Light", context)
                self.assertNotIn("event loop primitives", context)
                self.assertNotIn("pool exhaustion", context)

    def test_active_profile_vscode_compatible_format_all_sources(self):
        state_dir = self.create_state(mode="active")
        for source in ("startup", "resume", "new"):
            with self.subTest(source=source):
                payload = {
                    "hook_event_name": "SessionStart",
                    "session_id": f"sess-vscode-{source}",
                    "cwd": str(self.project),
                    "source": source,
                    "timestamp": "2026-10-15T12:00:00Z",
                }
                result = self.run_hook(payload)
                self.assertIsNotNone(result)
                self.assertIn("additionalContext", result)

                context = result["additionalContext"]
                self.assertIn(str(ROOT / "skills/learn/SKILL.md"), context)
                self.assertIn(str(state_dir), context)
                self.assertNotIn("Checkpoint frequency: Light", context)
                self.assertNotIn("event loop primitives", context)

    def test_nested_working_directory_resolves_repo_state(self):
        state_dir = self.create_state(mode="active")
        nested = self.project / "src" / "controllers"
        nested.mkdir(parents=True)

        payload = {
            "sessionId": "sess-nested-1",
            "cwd": str(nested),
            "source": "startup",
            "timestamp": 1729000000000,
        }
        result = self.run_hook(payload)
        self.assertIsNotNone(result)
        self.assertIn(str(state_dir), result["additionalContext"])

    def test_legacy_sensible_vibes_directory_restores_without_migration(self):
        legacy_dir = self.project / ".sensible-vibes"
        legacy_dir.mkdir()
        (legacy_dir / "profile.md").write_text(
            "# Learner Profile\nLearning mode: active\nOnboarding: complete\n", encoding="utf-8"
        )
        (legacy_dir / "project-map.md").write_text("# Project Map\n", encoding="utf-8")
        (legacy_dir / "progress.md").write_text("# Learning Progress\n", encoding="utf-8")

        payload = {
            "sessionId": "sess-legacy-1",
            "cwd": str(self.project),
            "source": "startup",
            "timestamp": 1729000000000,
        }
        result = self.run_hook(payload)
        self.assertIsNotNone(result)
        self.assertIn(str(legacy_dir), result["additionalContext"])

    def test_malformed_json_or_invalid_payload_fails_quietly(self):
        # Invalid JSON
        self.assertIsNone(self.run_hook("not json at all"))
        self.assertIsNone(self.run_hook("{bad json"))
        # Non-SessionStart event in VS Code format
        payload = {
            "hook_event_name": "PreToolUse",
            "session_id": "sess-1",
            "cwd": str(self.project),
        }
        self.assertIsNone(self.run_hook(payload))


if __name__ == "__main__":
    unittest.main()
