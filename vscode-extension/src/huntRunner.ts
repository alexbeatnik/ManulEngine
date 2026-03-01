import * as path from "path";
import * as fs from "fs";
import * as os from "os";
import { spawn, execSync, ChildProcess } from "child_process";
import * as vscode from "vscode";

/**
 * Probe candidate paths in order and return the first one that exists on disk.
 * Falls back to resolving via the shell `which`/`where` command, so pip
 * user-installs (~/.local/bin) and conda envs are found even if VS Code's
 * inherited PATH is trimmed.
 */
export function findManulExecutable(workspaceRoot: string): string {
  const custom = vscode.workspace
    .getConfiguration("manulEngine")
    .get<string>("manulPath", "")
    .trim();
  if (custom) {
    return custom;
  }

  const isWin = process.platform === "win32";

  // Ordered list of candidate paths to probe
  const candidates: string[] = [
    // 1. Project-local venv (cross-platform)
    isWin
      ? path.join(workspaceRoot, ".venv", "Scripts", "manul.exe")
      : path.join(workspaceRoot, ".venv", "bin", "manul"),
    // 2. pip --user install location (Linux / macOS)
    path.join(os.homedir(), ".local", "bin", "manul"),
    // 3. macOS Homebrew / pipx default bin
    path.join(os.homedir(), ".local", "pipx", "venvs", "manul-engine", "bin", "manul"),
    // 4. system-wide installs
    "/usr/local/bin/manul",
    "/usr/bin/manul",
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  // Last resort: ask the shell to find it (handles conda, pyenv, custom PATH)
  try {
    const cmd = isWin ? "where manul" : "which manul";
    const result = execSync(cmd, { encoding: "utf-8", timeout: 3000 }).trim().split("\n")[0].trim();
    if (result && fs.existsSync(result)) {
      return result;
    }
  } catch {
    // which/where failed — fall through to bare name and let spawn error naturally
  }

  return "manul"; // final fallback: rely on PATH at spawn time
}

/** Spawn manul <huntFile> and stream output. Resolves with exit code. */
export function runHunt(
  manulExe: string,
  huntFile: string,
  onData: (chunk: string) => void,
  token?: vscode.CancellationToken
): Promise<number> {
  return new Promise((resolve, reject) => {
    // Prefer the workspace folder root as cwd so ManulEngine picks up
    // manul_engine_configuration.json and cache paths from the project root.
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(
      vscode.Uri.file(huntFile)
    );
    const cwd = workspaceFolder?.uri.fsPath ?? path.dirname(huntFile);

    let proc: ChildProcess;
    try {
      proc = spawn(manulExe, [huntFile], {
        cwd,
        env: { ...process.env },
      });
    } catch (err) {
      reject(err);
      return;
    }

    proc.stdout?.on("data", (d: Buffer) => onData(d.toString()));
    proc.stderr?.on("data", (d: Buffer) => onData(d.toString()));
    proc.on("close", (code) => resolve(code ?? 1));
    proc.on("error", reject);

    token?.onCancellationRequested(() => {
      proc.kill();
      resolve(1);
    });
  });
}
