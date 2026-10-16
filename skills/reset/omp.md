# VibeWise Reset in omp

These notes adapt Claude Code tool and command names for omp (Oh My Pi). Follow SKILL.md
as written otherwise.

- Paths: `${CLAUDE_PLUGIN_ROOT}` is not expanded in omp. Run `reset.py` using `bash`
  from this file's directory with its absolute path. The Learn guide is `../learn/SKILL.md`
  relative to this file.
- Commands: suggest `/vibe-wise:learn` where SKILL.md says `/vibe-wise:learn`.
- Choices: where the guides mention AskUserQuestion, use the `ask` tool if available.
  If running non-interactively or `ask` is unavailable, ask the confirmation question
  in text. Then end your turn and wait for an explicit answer.
- Replies: ask the confirmation once, at the end of your reply. Don't add a
  closing line after it or quote these guides to the user.
