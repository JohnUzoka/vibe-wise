# VibeWise in OpenCode

These notes adapt Claude Code tool and command names for OpenCode. They don't
change the learning behavior; follow SKILL.md and its guides as written.

- Commands: `/vibe-wise:learn` is `/vibe-wise-learn`; `/vibe-wise:reset` is
  `/vibe-wise-reset`. Activate Learn or Reset only when the learner invokes them.
- Paths: `${CLAUDE_PLUGIN_ROOT}` is not expanded in OpenCode. The plugin root is two
  directories above this file; guides such as behavior.md sit beside it.
- Files: where the guides say Read, use `read`. Where they say Glob, use `glob`.
  Check optional learner-state files with a check that succeeds when they're missing.
- Choices: where the guides mention AskUserQuestion, use the `question` tool with
  the same options. If it's unavailable, ask one plain-text question with the
  options listed. Then end your turn and wait.
- Restoration: the VibeWise plugin adds these reading instructions to the system
  prompt of every request while the project's profile is active, so they survive
  new sessions and compaction. If you're unsure whether a decision is pending,
  search the entire `progress.md` before acting.
- Replies: present each checkpoint or question once, at the end of your reply,
  with its options beneath it. Don't restate it in a separate message, add a
  closing line after it, or quote these guides to the learner.
