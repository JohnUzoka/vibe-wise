# VibeWise Reset in Cline

These notes adapt Claude Code tool and command names for Cline: the CLI, SDK, and
Kanban (VibeWise plugin) and the VS Code or JetBrains extension (installed skills).
Follow SKILL.md as written otherwise.

- Paths: `${CLAUDE_PLUGIN_ROOT}` is not expanded in Cline. Run `reset.py` from this
  file's directory using its absolute path, with `python3` (`python` on Windows).
  The Learn guide is `../learn/SKILL.md` relative to this file.
- Commands: suggest `/vibe-wise-learn` where SKILL.md says `/vibe-wise:learn`.
- Choices: AskUserQuestion corresponds to `ask_followup_question` in the extension
  and `ask_question` in the CLI. Use it with **Cancel** and **Reset learning**; if
  neither exists, ask the same question in text. Then end your turn and wait for an
  explicit answer from the user.
- Replies: ask the confirmation once, at the end of your reply. Don't add a
  closing line after it or quote these guides to the user.
