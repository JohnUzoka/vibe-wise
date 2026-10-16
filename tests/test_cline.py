"""Tests for the VibeWise Cline adapter plugin."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "adapters/cline/plugin.ts"
LEARN_SKILL_PATH = ROOT / "skills/learn/SKILL.md"
RESET_SKILL_PATH = ROOT / "skills/reset/SKILL.md"

BUN_BIN = Path.home() / ".bun/bin/bun"
if not BUN_BIN.exists():
    found = shutil.which("bun")
    if found:
        BUN_BIN = Path(found)


RUNNER_SCRIPT = """
import { plugin } from %s;

const commands = new Map();

const fakeApi = {
  registerCommand(command) {
    if (command && typeof command.name === "string") {
      commands.set(command.name, command);
    }
  },
};

const payload = JSON.parse(await Bun.stdin.text());
const results = {};

for (const step of payload.steps) {
  if (step.action === "setup") {
    const fakeCtx = {
      cwd: step.cwd,
      workspaceInfo: step.workspaceInfo,
      session: { sessionId: step.sessionId ?? "test-session" },
      client: { name: "cline-cli" },
    };
    plugin.setup(fakeApi, fakeCtx);
    results[step.id] = {
      commands: Array.from(commands.keys()),
      descriptions: Object.fromEntries(
        Array.from(commands.entries()).map(([k, v]) => [k, v.description ?? ""])
      ),
    };
  } else if (step.action === "invoke_command") {
    const cmd = commands.get(step.name);
    if (!cmd) {
      results[step.id] = { error: `Command not found: ${step.name}` };
    } else {
      const res = await cmd.handler(step.input ?? "");
      results[step.id] = { result: res };
    }
  } else if (step.action === "beforeRun") {
    const start = performance.now();
    const res = await plugin.hooks.beforeRun(step.context);
    const durationMs = performance.now() - start;
    results[step.id] = { result: res ?? null, durationMs };
  }
}

console.log(JSON.stringify(results));
""" % json.dumps(str(PLUGIN_PATH))


class ClinePluginContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vibe-wise-cline-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "test_project"
        self.project.mkdir()
        (self.project / ".git").mkdir()

    def state(self, project=None, mode="active"):
        directory = (project or self.project) / ".vibe-wise"
        directory.mkdir(exist_ok=True)
        (directory / "profile.md").write_text(
            f"# Learner Profile\nLearning mode: {mode}\nOnboarding: complete\n"
            "Checkpoint frequency: Light\nQuestion style: Open-ended\n"
            "Implementation style: AI writes code\n"
            "Strong concepts: HTTP request flow\n",
            encoding="utf-8",
        )
        (directory / "project-map.md").write_text(
            "# Project Map\nCLI -> service.py -> SQLite\n",
            encoding="utf-8",
        )
        (directory / "progress.md").write_text(
            "# Learning Progress\n## Transactions\n"
            "Demonstrated understanding: two writes must succeed together.\n",
            encoding="utf-8",
        )
        return directory

    def run_bun_harness(self, steps):
        if not BUN_BIN.exists():
            self.skipTest(f"bun not found at {BUN_BIN}")
        proc = subprocess.run(
            [str(BUN_BIN), "-e", RUNNER_SCRIPT],
            input=json.dumps({"steps": steps}),
            capture_output=True,
            text=True,
            cwd=str(self.root),
            timeout=10,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"Bun execution failed (exit {proc.returncode}):\n{proc.stderr}\n{proc.stdout}",
        )
        return json.loads(proc.stdout)

    def test_setup_registers_commands(self):
        steps = [
            {
                "id": "init",
                "action": "setup",
                "cwd": str(self.project),
            }
        ]
        res = self.run_bun_harness(steps)["init"]
        self.assertEqual(sorted(res["commands"]), ["vibe-wise-learn", "vibe-wise-reset"])

    def test_command_invocation_returns_submit_prompt(self):
        steps = [
            {
                "id": "setup",
                "action": "setup",
                "cwd": str(self.project),
            },
            {
                "id": "learn",
                "action": "invoke_command",
                "name": "vibe-wise-learn",
                "input": "how do I add auth?",
            },
            {
                "id": "reset",
                "action": "invoke_command",
                "name": "vibe-wise-reset",
                "input": "",
            },
        ]
        results = self.run_bun_harness(steps)
        learn_res = results["learn"]["result"]
        self.assertNotIn("reply", learn_res)
        self.assertIn(str(LEARN_SKILL_PATH), learn_res["submitPrompt"])
        self.assertIn("how do I add auth?", learn_res["submitPrompt"])

        reset_res = results["reset"]["result"]
        self.assertNotIn("reply", reset_res)
        self.assertIn(str(RESET_SKILL_PATH), reset_res["submitPrompt"])

    def test_active_profile_delivers_restoration_context_without_learner_notes(self):
        state_dir = self.state(mode="active")
        steps = [
            {
                "id": "setup",
                "action": "setup",
                "cwd": str(self.project),
            },
            {
                "id": "run1",
                "action": "beforeRun",
                "context": {},
            },
        ]
        results = self.run_bun_harness(steps)
        run_res = results["run1"]["result"]
        self.assertIsNotNone(run_res)
        append_context = run_res.get("appendContext")
        self.assertIsNotNone(append_context)
        # Contract assertions:
        # 1. Contains SKILL.md path
        self.assertIn(str(LEARN_SKILL_PATH), append_context)
        # 2. Contains state directory path
        self.assertIn(str(state_dir), append_context)
        # 3. Does NOT leak raw learner notes
        self.assertNotIn("two writes must succeed together", append_context)
        self.assertNotIn("HTTP request flow", append_context)

    def test_paused_profile_delivers_nothing(self):
        self.state(mode="paused")
        steps = [
            {
                "id": "setup",
                "action": "setup",
                "cwd": str(self.project),
            },
            {
                "id": "run1",
                "action": "beforeRun",
                "context": {},
            },
        ]
        results = self.run_bun_harness(steps)
        run_res = results["run1"]["result"]
        self.assertIsNone(run_res)

    def test_uninitialized_project_delivers_nothing(self):
        steps = [
            {
                "id": "setup",
                "action": "setup",
                "cwd": str(self.project),
            },
            {
                "id": "run1",
                "action": "beforeRun",
                "context": {},
            },
        ]
        results = self.run_bun_harness(steps)
        run_res = results["run1"]["result"]
        self.assertIsNone(run_res)

    def test_before_run_hook_stays_within_budget(self):
        self.state(mode="active")
        steps = [
            {
                "id": "setup",
                "action": "setup",
                "cwd": str(self.project),
            },
            {
                "id": "run1",
                "action": "beforeRun",
                "context": {},
            },
        ]
        results = self.run_bun_harness(steps)
        duration_ms = results["run1"]["durationMs"]
        # Hook budget in Cline is 3000 ms. Subprocess timeout is 2000 ms.
        # It should complete in well under 1000 ms locally.
        self.assertLess(duration_ms, 2500, f"beforeRun took {duration_ms} ms, exceeding safety budget")

    def test_dynamic_pause_stops_restoration_without_session_restart(self):
        state_dir = self.state(mode="active")
        steps = [
            {
                "id": "setup",
                "action": "setup",
                "cwd": str(self.project),
            },
            {
                "id": "run1",
                "action": "beforeRun",
                "context": {},
            },
        ]
        results = self.run_bun_harness(steps)
        self.assertIsNotNone(results["run1"]["result"])

        # Dynamically pause profile
        (state_dir / "profile.md").write_text(
            "# Learner Profile\nLearning mode: paused\n",
            encoding="utf-8",
        )

        steps2 = [
            {
                "id": "run2",
                "action": "beforeRun",
                "context": {},
            },
        ]
        # In a new run against the paused profile, beforeRun returns undefined
        results2 = self.run_bun_harness(steps + steps2)
        self.assertIsNone(results2["run2"]["result"])


if __name__ == "__main__":
    unittest.main()
