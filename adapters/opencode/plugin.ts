import type { Plugin } from "@opencode-ai/plugin";
import { execFile } from "node:child_process";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

// Resolve the plugin root from this file, never from cwd. Users load it through a
// one-line re-export in OpenCode's plugin directory, so this is the real checkout.
const pluginRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const sessionStartScript = path.join(pluginRoot, "hooks", "session_start.py");
const guide = (skill: string) => path.join(pluginRoot, "skills", skill, "SKILL.md");

/** Plain-text restoration instructions, or null when learning isn't active here. */
async function restorationContext(directory: string): Promise<string | null> {
	try {
		const { stdout } = await execFileAsync(
			process.platform === "win32" ? "python" : "python3",
			[sessionStartScript, "--cwd", directory],
			{ timeout: 5000, encoding: "utf-8", maxBuffer: 64 * 1024 },
		);
		return stdout.trim() || null;
	} catch {
		return null; // Learning must never block a session.
	}
}

export const VibeWise: Plugin = async ({ client, directory }) => {
	// One OpenCode server can host sessions in several directories; each session's
	// own directory selects its notes. It never changes, so cache it per session.
	const sessionDirectories = new Map<string, string>();
	const directoryFor = async (sessionID?: string) => {
		if (!sessionID) return directory;
		let found = sessionDirectories.get(sessionID);
		if (!found) {
			const response = await client.session.get({ path: { id: sessionID } }).catch(() => null);
			found = response?.data?.directory ?? directory;
			sessionDirectories.set(sessionID, found);
		}
		return found;
	};

	return {
		config: async (config) => {
			// Explicit entry points; the templates run in the main conversation.
			config.command ??= {};
			for (const [name, skill, description] of [
				["vibe-wise-learn", "learn", "Activate or resume VibeWise learning-first development"],
				["vibe-wise-reset", "reset", "Back up this project's VibeWise notes and restart onboarding"],
			] as const) {
				config.command[name] ??= {
					description,
					template: `Read and follow the VibeWise ${skill === "learn" ? "Learn" : "Reset"} guide at:\n${guide(skill)}\n\n$ARGUMENTS`,
				};
			}
			// The guides and reset.py live outside the project, and OpenCode asks
			// before touching external paths (non-interactive runs auto-reject).
			// Allow only this plugin's skills folder, and never override a deny.
			const permission = (config.permission ??= {}) as Record<string, unknown>;
			const external = permission.external_directory;
			if (external === "deny") return;
			const rules =
				typeof external === "object" && external !== null
					? (external as Record<string, string>)
					: { "*": (external as string | undefined) ?? "ask" };
			rules[path.join(pluginRoot, "skills", "**")] ??= "allow";
			permission.external_directory = rules;
		},
		// The system prompt is rebuilt for every request, so this survives new
		// sessions, resumes, and compaction alike. The profile is re-checked each
		// time, so pausing learning stops it immediately.
		"experimental.chat.system.transform": async (input, output) => {
			const text = await restorationContext(await directoryFor(input.sessionID));
			if (text) output.system.push(text);
		},
	};
};
