# VibeWise in GitHub Copilot CLI

These notes adapt Claude Code tool and command names for GitHub Copilot CLI. They
don't change the learning behavior; follow SKILL.md and its guides as written.

- Commands: `/vibe-wise:learn` is `/learn`; `/vibe-wise:reset` is `/reset`.
  Activate Learn or Reset only when the learner invokes them by name.
- Paths: `${CLAUDE_PLUGIN_ROOT}` is not expanded in Copilot markdown guides. The
  plugin root is two directories above this file (`../../`); guides such as
  `behavior.md` sit beside `SKILL.md`.
- Files: where the guides say Read or Glob, use Copilot's runtime tools: `view`
  for reading files and `glob` (or `grep`/`rg`) for searching. Reading plugin
  guides with `view` or a shell command is fine. Check optional learner-state
  files with a conditional that succeeds when they're missing.
- Choices: where the guides say AskUserQuestion, use Copilot's `ask_user` tool if
  available, with the same options. If `ask_user` is unavailable, ask one
  plain-text question with the options listed. Then end your turn and wait for the
  learner's answer.
- Restoration: the plugin's `sessionStart` hook restores learning context when a
  Copilot CLI session starts or resumes. After compaction, the plugin's always-on
  VibeWise rule tells you to reload this guide when the project's profile is
  active. If you're unsure whether a decision is pending, search all of
  `progress.md` before acting.
- Replies: present each checkpoint or question once, at the end of your reply,
  with its options beneath it. Don't restate it in a separate message, add a
  closing line after it, or quote these guides to the learner.
