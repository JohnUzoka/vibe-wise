# VibeWise Reset in Cline

These notes adapt Claude Code tool and command names for Cline (CLI, SDK, and
Kanban plugins). Follow SKILL.md as written otherwise.

- Paths: `${CLAUDE_PLUGIN_ROOT}` is not expanded in Cline. Run `reset.py` from
  this file's directory using its absolute path (or invoke via `run_commands` with
  `python3`). The Learn guide is `../learn/SKILL.md` relative to this file.
- Commands: suggest `/vibe-wise-learn` where SKILL.md says `/vibe-wise:learn`.
- Choices: AskUserQuestion corresponds to `ask_question`. Use `ask_question` with the
  confirmation question and options (**Cancel** and **Reset learning**). If
  `ask_question` is unavailable in your environment, ask the same question in text.
  Then end your turn and wait for an explicit answer from the user.
- Replies: ask the confirmation once, at the end of your reply. Don't add a
  closing line after it or quote these guides to the user.
