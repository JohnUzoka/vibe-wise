import type {
	AgentExtensionCommand,
	AgentExtensionCommandResult,
	AgentHooks,
	AgentPlugin,
} from "@cline/core";
import { execFile } from "node:child_process";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
type PluginSetup = NonNullable<AgentPlugin["setup"]>;

// Resolve plugin root from this file's own location, never from cwd. Cline loads
// plugins through jiti, which evaluates them from a `data:` URL but supplies the
// real `__dirname`; plain ESM hosts fall back to the module URL.
const adapterDir =
	typeof __dirname === "string"
		? __dirname
		: path.dirname(fileURLToPath(import.meta.url));
const pluginRoot = path.resolve(adapterDir, "../..");
const sessionStartScript = path.join(pluginRoot, "hooks", "session_start.py");
const learnSkillPath = path.join(pluginRoot, "skills", "learn", "SKILL.md");
const resetSkillPath = path.join(pluginRoot, "skills", "reset", "SKILL.md");

/**
 * Execute session_start.py in cwd mode with a short timeout.
 * Returns plain-text restoration instructions when active, or null when
 * inactive/paused/missing/failed. Learning must never block a session.
 * The 2-second timeout stays comfortably within the 3-second hook deadline.
 */
async function getRestorationContext(cwd: string): Promise<string | null> {
	if (!cwd || typeof cwd !== "string") {
		return null;
	}
	const pythonBin = process.platform === "win32" ? "python" : "python3";
	try {
		const { stdout } = await execFileAsync(
			pythonBin,
			[sessionStartScript, "--cwd", cwd],
			{
				timeout: 2000,
				encoding: "utf-8",
				maxBuffer: 64 * 1024,
			},
		);
		const trimmed = stdout.trim();
		return trimmed.length > 0 ? trimmed : null;
	} catch {
		return null;
	}
}

// Plugins run in one worker per session, so module state is per session. The
// session directory, not the plugin store or host cwd, selects the learner's notes.
let sessionCwd: string | undefined;

// Explicit entry points. submitPrompt sends the instruction through the normal
// prompt flow, so the guide is followed in the main conversation.
const guideCommand =
	(label: string, guide: string) =>
	(input: string): AgentExtensionCommandResult => {
		const request = input.trim() ? `\n\nUser request: ${input.trim()}` : "";
		return {
			submitPrompt: `Read and follow the VibeWise ${label} guide at:\n${guide}${request}`,
		};
	};

export const plugin: AgentPlugin = {
	name: "vibe-wise",
	manifest: {
		capabilities: ["hooks", "commands"],
	},

	setup(api: Parameters<PluginSetup>[0], ctx: Parameters<PluginSetup>[1]) {
		sessionCwd = ctx?.cwd;
		api.registerCommand({
			name: "vibe-wise-learn",
			description: "Activate or resume learning-first development with VibeWise",
			handler: guideCommand("Learn", learnSkillPath),
		} satisfies AgentExtensionCommand);
		api.registerCommand({
			name: "vibe-wise-reset",
			description:
				"Back up this project's learning notes and restart onboarding after confirmation",
			handler: guideCommand("Reset", resetSkillPath),
		} satisfies AgentExtensionCommand);
	},

	hooks: {
		// Re-checked on every run so pausing learning mid-session stops restoration.
		async beforeRun() {
			if (!sessionCwd) return undefined;
			const text = await getRestorationContext(sessionCwd);
			return text ? { appendContext: text } : undefined;
		},
	} satisfies AgentHooks,
};

export default plugin;
