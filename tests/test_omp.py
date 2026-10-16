"""Tests for the VibeWise omp (Oh My Pi) adapter extension."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXTENSION_PATH = ROOT / "adapters/omp/extension.ts"

BUN_BIN = Path.home() / ".bun/bin/bun"
if not BUN_BIN.exists():
    found = shutil.which("bun")
    if found:
        BUN_BIN = Path(found)


RUNNER_SCRIPT = """
import vibeWiseExtension from %s;

const handlers = new Map();
const commands = new Map();
const userMessages = [];
const customMessages = [];

const fakePi = {
  on(event, handler) {
    if (!handlers.has(event)) handlers.set(event, []);
    handlers.get(event).push(handler);
  },
  registerCommand(name, options) {
    commands.set(name, options);
  },
  sendUserMessage(content, options) {
    userMessages.push({ content, options });
  },
  sendMessage(message, options) {
    customMessages.push({ message, options });
  },
};

vibeWiseExtension(fakePi);

const payload = JSON.parse(await Bun.stdin.text());
const results = {};

for (const step of payload.steps) {
  if (step.action === "inspect_commands") {
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
      userMessages.length = 0;
      customMessages.length = 0;
      await cmd.handler(step.args ?? "", { cwd: step.cwd ?? "" });
      results[step.id] = {
        userMessages: [...userMessages],
        customMessages: [...customMessages],
      };
    }
  } else if (step.action === "emit") {
    const list = handlers.get(step.event) ?? [];
    let lastResult = null;
    const ctx = { cwd: step.cwd ?? "" };
    for (const h of list) {
      const res = await h(step.eventData ?? { type: step.event }, ctx);
      if (res !== undefined) lastResult = res;
    }
    results[step.id] = { result: lastResult };
  }
}

console.log(JSON.stringify(results));
""" % json.dumps(str(EXTENSION_PATH))


class OmpAdapterTests(unittest.TestCase):
    def setUp(self):
        if not BUN_BIN.exists():
            self.skipTest(f"bun binary not found at {BUN_BIN}")
        self.temp = tempfile.TemporaryDirectory(prefix="vibewise-omp-test-")
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / ".git").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def state(self, project=None, mode="active"):
        directory = (project or self.project) / ".vibe-wise"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "profile.md").write_text(
            f"# Learner Profile\nLearning mode: {mode}\nOnboarding: complete\n"
            "Checkpoint frequency: Light\nQuestion style: Open-ended\n"
            "Implementation style: AI writes code\n"
            "Strong concepts: HTTP request flow\n",
            encoding="utf-8",
        )
        (directory / "project-map.md").write_text(
            "# Project Map\nCLI → service.py → SQLite\n",
            encoding="utf-8",
        )
        (directory / "progress.md").write_text(
            "# Learning Progress\n## Transactions\n"
            "Demonstrated understanding: two writes must succeed together.\n"
            "## Queues\nNeeds reinforcement: retries.\n",
            encoding="utf-8",
        )
        return directory

    def run_steps(self, steps):
        proc = subprocess.run(
            [str(BUN_BIN), "-e", RUNNER_SCRIPT],
            input=json.dumps({"steps": steps}),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"Bun execution failed (exit {proc.returncode}):\n{proc.stderr}\n{proc.stdout}",
        )
        return json.loads(proc.stdout)

    def test_commands_registered_and_functional(self):
        steps = [
            {"id": "list", "action": "inspect_commands"},
            {"id": "run_learn", "action": "invoke_command", "name": "vibe-wise:learn", "args": ""},
            {"id": "run_reset", "action": "invoke_command", "name": "vibe-wise:reset", "args": "now"},
        ]
        res = self.run_steps(steps)
        cmds = res["list"]["commands"]
        self.assertIn("vibe-wise:learn", cmds)
        self.assertIn("vibe-wise:reset", cmds)

        learn_msgs = res["run_learn"]["userMessages"]
        self.assertEqual(len(learn_msgs), 1)
        learn_text = learn_msgs[0]["content"]
        self.assertIn(str(ROOT / "skills/learn/SKILL.md"), learn_text)
        self.assertIn("read", learn_text.lower())

        reset_msgs = res["run_reset"]["userMessages"]
        self.assertEqual(len(reset_msgs), 1)
        reset_text = reset_msgs[0]["content"]
        self.assertIn(str(ROOT / "skills/reset/SKILL.md"), reset_text)
        self.assertIn("now", reset_text)

    def test_active_project_injects_restoration(self):
        state_dir = self.state()
        steps = [
            {
                "id": "turn1",
                "action": "emit",
                "event": "before_agent_start",
                "cwd": str(self.project),
            }
        ]
        res = self.run_steps(steps)
        turn1 = res["turn1"]["result"]
        self.assertIsNotNone(turn1)
        self.assertIn("message", turn1)
        content = turn1["message"]["content"]
        self.assertIn(str(ROOT / "skills/learn/SKILL.md"), content)
        self.assertIn(str(state_dir), content)

    def test_restoration_not_duplicated_on_second_turn(self):
        self.state()
        steps = [
            {
                "id": "turn1",
                "action": "emit",
                "event": "before_agent_start",
                "cwd": str(self.project),
            },
            {
                "id": "turn2",
                "action": "emit",
                "event": "before_agent_start",
                "cwd": str(self.project),
            },
        ]
        res = self.run_steps(steps)
        self.assertIsNotNone(res["turn1"]["result"])
        self.assertIsNone(res["turn2"]["result"])

    def test_paused_project_injects_nothing(self):
        self.state(mode="paused")
        steps = [
            {
                "id": "turn",
                "action": "emit",
                "event": "before_agent_start",
                "cwd": str(self.project),
            }
        ]
        res = self.run_steps(steps)
        self.assertIsNone(res["turn"]["result"])

    def test_no_state_project_injects_nothing(self):
        steps = [
            {
                "id": "turn",
                "action": "emit",
                "event": "before_agent_start",
                "cwd": str(self.project),
            }
        ]
        res = self.run_steps(steps)
        self.assertIsNone(res["turn"]["result"])

    def test_session_compacting_feeds_context_for_active_only(self):
        state_dir = self.state()
        steps = [
            {
                "id": "compact_active",
                "action": "emit",
                "event": "session.compacting",
                "cwd": str(self.project),
            }
        ]
        res = self.run_steps(steps)
        compact_res = res["compact_active"]["result"]
        self.assertIsNotNone(compact_res)
        self.assertIn("context", compact_res)
        ctx_list = compact_res["context"]
        self.assertEqual(len(ctx_list), 1)
        self.assertIn(str(ROOT / "skills/learn/SKILL.md"), ctx_list[0])
        self.assertIn(str(state_dir), ctx_list[0])

        # Paused profile should not feed into compacting context
        paused_proj = self.root / "paused_proj"
        paused_proj.mkdir()
        (paused_proj / ".git").mkdir()
        self.state(project=paused_proj, mode="paused")
        steps_paused = [
            {
                "id": "compact_paused",
                "action": "emit",
                "event": "session.compacting",
                "cwd": str(paused_proj),
            }
        ]
        res_paused = self.run_steps(steps_paused)
        self.assertIsNone(res_paused["compact_paused"]["result"])

    def test_restoration_redelivered_after_compaction_event(self):
        self.state()
        steps = [
            {
                "id": "turn1",
                "action": "emit",
                "event": "before_agent_start",
                "cwd": str(self.project),
            },
            {
                "id": "turn2",
                "action": "emit",
                "event": "before_agent_start",
                "cwd": str(self.project),
            },
            {
                "id": "compact",
                "action": "emit",
                "event": "session_compact",
                "cwd": str(self.project),
            },
            {
                "id": "turn3",
                "action": "emit",
                "event": "before_agent_start",
                "cwd": str(self.project),
            },
        ]
        res = self.run_steps(steps)
        self.assertIsNotNone(res["turn1"]["result"])
        self.assertIsNone(res["turn2"]["result"])
        self.assertIsNotNone(res["turn3"]["result"])

    def test_session_start_and_switch_reset_delivery(self):
        self.state()
        for reset_event in ("session_start", "session_switch", "session_branch"):
            with self.subTest(reset_event=reset_event):
                steps = [
                    {
                        "id": "turn1",
                        "action": "emit",
                        "event": "before_agent_start",
                        "cwd": str(self.project),
                    },
                    {
                        "id": "reset",
                        "action": "emit",
                        "event": reset_event,
                        "cwd": str(self.project),
                    },
                    {
                        "id": "turn2",
                        "action": "emit",
                        "event": "before_agent_start",
                        "cwd": str(self.project),
                    },
                ]
                res = self.run_steps(steps)
                self.assertIsNotNone(res["turn1"]["result"])
                self.assertIsNotNone(res["turn2"]["result"])


if __name__ == "__main__":
    unittest.main()
