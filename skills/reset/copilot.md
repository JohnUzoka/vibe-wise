# VibeWise Reset in GitHub Copilot CLI

These notes adapt Claude Code tool and command names for GitHub Copilot CLI. Follow
SKILL.md as written otherwise.

- Paths: `${CLAUDE_PLUGIN_ROOT}` is not expanded in Copilot markdown guides. Run
  `reset.py` from this file's directory using its absolute path (or resolve it
  relative to this file). The Learn guide is `../learn/SKILL.md` relative to this file.
- Commands: suggest `/learn` where SKILL.md says `/vibe-wise:learn`.
- Choices: where SKILL.md mentions AskUserQuestion, use Copilot's `ask_user` tool
  if available, with the same options (**Cancel** and **Reset learning**). If
  `ask_user` is unavailable, ask the confirmation in plain text with the options
  listed. Then end your turn and wait for an explicit answer before running
  `reset.py --confirm`.
- Replies: ask the confirmation once, at the end of your reply. Don't add a
  closing line after it or quote these guides to the user.
