/**
 * CodeLens provider for `.hunt` files — shows a clickable "🔍 Explain Heuristics"
 * lens above each actionable step line (Click, Fill, Select, Hover, etc.).
 *
 * Clicking the lens runs the entire hunt file with `--explain` and routes
 * the heuristic score breakdown to the "ManulEngine: Explain Heuristics"
 * output channel.
 */

import * as vscode from "vscode";
import * as path from "path";
import { findManulExecutable } from "./huntRunner";
import { EXPLAIN_OUTPUT_CHANNEL } from "./constants";

// ── Step-line detection ────────────────────────────────────────────────────
// Matches lines that trigger element resolution (heuristic scoring).
// System-only keywords (NAVIGATE, WAIT, PRESS ENTER, SCROLL, DONE, etc.)
// are excluded because they don't resolve DOM elements.
const ACTION_RE = /^\s*(?:\d+\.\s+)?(?:Click|CLICK|DOUBLE\s+CLICK|Fill|Type|Select|Choose|Check|Uncheck|HOVER|Drag|RIGHT\s+CLICK|EXTRACT|VERIFY(?:\s+SOFTLY)?(?:\s+VISUAL)?)\b/i;

// Lines to skip — metadata, comments, blanks, system-only keywords
const SKIP_RE = /^\s*(?:$|#|@|STEP\b|NAVIGATE\b|WAIT\b|PRESS\s+ENTER\b|SCROLL\b|DONE\b|SET\b|SCAN\b|MOCK\b|WAIT\s+FOR\b|CALL\b|OPEN\b|UPLOAD\b|DEBUG\b|PAUSE\b|\[SETUP\]|\[TEARDOWN\]|\[END)/i;

export class ExplainLensProvider implements vscode.CodeLensProvider {
  private _onDidChange = new vscode.EventEmitter<void>();
  readonly onDidChangeCodeLenses = this._onDidChange.event;

  provideCodeLenses(
    document: vscode.TextDocument,
    _token: vscode.CancellationToken
  ): vscode.CodeLens[] {
    if (document.languageId !== "hunt") { return []; }

    const enabled = vscode.workspace
      .getConfiguration("manulEngine")
      .get<boolean>("explainCodeLens", true);
    if (!enabled) { return []; }

    const lenses: vscode.CodeLens[] = [];
    for (let i = 0; i < document.lineCount; i++) {
      const line = document.lineAt(i);
      const text = line.text;
      if (SKIP_RE.test(text)) { continue; }
      if (!ACTION_RE.test(text)) { continue; }

      const range = new vscode.Range(i, 0, i, text.length);
      lenses.push(
        new vscode.CodeLens(range, {
          title: "🔍 Explain Heuristics",
          command: "manul.explainHuntFile",
          arguments: [document.uri],
          tooltip: "Run this hunt file with --explain to see the heuristic score breakdown for each element resolution",
        })
      );
    }
    return lenses;
  }
}

// ── Explain command execution ──────────────────────────────────────────────

let _explainChannel: vscode.OutputChannel | undefined;

function getExplainChannel(): vscode.OutputChannel {
  if (!_explainChannel) {
    _explainChannel = vscode.window.createOutputChannel(EXPLAIN_OUTPUT_CHANNEL);
  }
  return _explainChannel;
}

/**
 * Run the hunt file with `--explain` and stream output to the dedicated
 * output channel.  Called by the CodeLens command.
 */
export async function explainHuntFile(uri?: vscode.Uri): Promise<void> {
  const target = uri ?? vscode.window.activeTextEditor?.document.uri;
  if (!target || !target.fsPath.endsWith(".hunt")) {
    vscode.window.showWarningMessage("Please open or select a .hunt file.");
    return;
  }

  const roots = vscode.workspace.workspaceFolders ?? [];
  const workspaceRoot =
    vscode.workspace.getWorkspaceFolder(target)?.uri.fsPath
    ?? roots[0]?.uri.fsPath
    ?? path.dirname(target.fsPath);

  const manulExe = await findManulExecutable(workspaceRoot);

  const channel = getExplainChannel();
  channel.clear();
  channel.show(); // reveal and focus

  const fileName = path.basename(target.fsPath);
  channel.appendLine(`🔍 ManulEngine Explain — ${fileName}`);
  channel.appendLine(`   File: ${target.fsPath}`);
  channel.appendLine("─".repeat(70));
  channel.appendLine("");

  try {
    const exitCode = await runExplain(manulExe, target.fsPath, (chunk) => {
      channel.append(chunk);
    });

    channel.appendLine("");
    channel.appendLine("─".repeat(70));
    if (exitCode === 0) {
      channel.appendLine("✅ Explain run complete.");
    } else {
      channel.appendLine(`⚠️ Explain run finished with exit code ${exitCode}.`);
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    channel.appendLine(`❌ Explain run failed: ${msg}`);
  }
}

/**
 * Spawn `manul --explain --workers 1 <huntFile>`.
 * This is a simplified variant of `runHunt` that always injects `--explain`.
 */
function runExplain(
  manulExe: string,
  huntFile: string,
  onData: (chunk: string) => void
): Promise<number> {
  // We import spawn here to keep the module self-contained vs huntRunner.
  const { spawn } = require("child_process") as typeof import("child_process");

  return new Promise((resolve, reject) => {
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(
      vscode.Uri.file(huntFile)
    );
    const cwd = workspaceFolder?.uri.fsPath ?? path.dirname(huntFile);

    // ── Browser selection from VS Code settings ────────────────────────────
    const browserRaw = vscode.workspace
      .getConfiguration("manulEngine")
      .get<string>("browser", "chromium");
    const browserVal = (browserRaw || "chromium").trim().toLowerCase();
    const isChannel = browserVal === "chrome" || browserVal === "msedge";
    const explainBrowserArgs = isChannel
      ? ["--browser", "chromium"]
      : ["--browser", browserVal];

    const spawnArgs = [...explainBrowserArgs, "--explain", "--workers", "1"];

    // Pull reporting flags from VS Code settings (same as runHunt)
    const cfg = vscode.workspace.getConfiguration("manulEngine");
    const retries = cfg.get<number>("retries", 0);
    if (retries > 0) { spawnArgs.push("--retries", String(retries)); }
    const screenshot = cfg.get<string>("screenshotMode", "on-fail");
    if (screenshot && screenshot !== "on-fail") { spawnArgs.push("--screenshot", screenshot); }
    if (cfg.get<boolean>("htmlReport", false)) { spawnArgs.push("--html-report"); }

    spawnArgs.push(huntFile);

    try {
      const env: NodeJS.ProcessEnv = { ...process.env, PYTHONUNBUFFERED: "1" };
      if (isChannel) { env.MANUL_CHANNEL = browserVal; }
      if (vscode.workspace.getConfiguration("manulEngine").get<boolean>("autoAnnotate", false)) {
        env.MANUL_AUTO_ANNOTATE = "1";
      }
      const proc = spawn(manulExe, spawnArgs, { cwd, env });

      proc.stdout?.on("data", (d: Buffer) => onData(d.toString()));
      proc.stderr?.on("data", (d: Buffer) => onData(d.toString()));
      proc.on("close", (code) => resolve(code ?? 1));
      proc.on("error", reject);
    } catch (err) {
      reject(err);
    }
  });
}

/** Dispose the explain output channel (called from extension deactivate). */
export function disposeExplainChannel(): void {
  _explainChannel?.dispose();
  _explainChannel = undefined;
}
