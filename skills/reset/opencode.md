# VibeWise Reset in OpenCode

These notes adapt Claude Code tool and command names for OpenCode. Follow SKILL.md
as written otherwise.

- Paths: `${CLAUDE_PLUGIN_ROOT}` is not expanded in OpenCode. Run `reset.py` with
  `bash`, from this file's directory using its absolute path. The Learn guide is
  `../learn/SKILL.md` relative to this file.
- Commands: suggest `/vibe-wise-learn` where SKILL.md says `/vibe-wise:learn`.
- Choices: where SKILL.md mentions AskUserQuestion, use the `question` tool with
  **Cancel** and **Reset learning**. If it's unavailable, ask the same question in
  text. Then end your turn and wait for an explicit answer.
- Replies: ask the confirmation once, at the end of your reply. Don't add a
  closing line after it or quote these guides to the user.
