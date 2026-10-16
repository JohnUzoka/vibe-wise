import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { execFile } from "node:child_process";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

// Resolve plugin root from this file's own location, never from cwd.
const extensionDir =
	typeof import.meta.dir === "string"
		? import.meta.dir
		: path.dirname(fileURLToPath(import.meta.url));
const pluginRoot = path.resolve(extensionDir, "../..");
const sessionStartScript = path.join(pluginRoot, "hooks", "session_start.py");
const learnSkillPath = path.join(pluginRoot, "skills", "learn", "SKILL.md");
const resetSkillPath = path.join(pluginRoot, "skills", "reset", "SKILL.md");

/**
 * Execute session_start.py in cwd mode with a short timeout.
 * Returns plain-text restoration instructions when active, or null when
 * inactive/paused/missing/failed. Learning must never block a session.
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
				timeout: 5000,
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

export default function vibeWiseExtension(pi: ExtensionAPI): void {
	// Track whether restoration instructions have been delivered for the active session.
	let restorationDelivered = false;

	// Reset delivery flag when switching or starting a session
	pi.on("session_start", async () => {
		restorationDelivered = false;
	});

	pi.on("session_switch", async () => {
		restorationDelivered = false;
	});

	pi.on("session_branch", async () => {
		restorationDelivered = false;
	});

	pi.on("session_tree", async () => {
		restorationDelivered = false;
	});

	// On each new agent turn where restoration hasn't been delivered yet,
	// check the project profile and inject instructions if active.
	pi.on("before_agent_start", async (_event, ctx) => {
		if (restorationDelivered) {
			return;
		}
		const text = await getRestorationContext(ctx.cwd);
		if (!text) {
			return;
		}
		restorationDelivered = true;
		return {
			message: {
				customType: "vibewise",
				content: text,
				display: true,
			},
		};
	});

	// Feed restoration instructions into compaction context so learning state survives.
	pi.on("session.compacting", async (_event, ctx) => {
		const text = await getRestorationContext(ctx.cwd);
		if (!text) {
			return;
		}
		return {
			context: [text],
		};
	});

	// Once compaction completes, mark restoration as needing re-delivery on subsequent turns.
	pi.on("session_compact", async () => {
		restorationDelivered = false;
	});

	// Explicit entry points. sendUserMessage goes through the normal prompt flow, so
	// the guide is followed in the main conversation, as with Claude's skill command.
	const guideCommand = (label: string, guide: string) => async (args: string) => {
		const request = args?.trim() ? `\n\nUser request: ${args.trim()}` : "";
		pi.sendUserMessage(
			`Use read to load the VibeWise ${label} guide and follow it in the main conversation:\n${guide}${request}`,
		);
	};
	pi.registerCommand("vibe-wise:learn", {
		description: "Activate or resume learning-first development with VibeWise",
		handler: guideCommand("Learn", learnSkillPath),
	});
	pi.registerCommand("vibe-wise:reset", {
		description: "Back up this project's learning notes and restart onboarding after confirmation",
		handler: guideCommand("Reset", resetSkillPath),
	});
}
