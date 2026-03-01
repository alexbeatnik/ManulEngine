import * as path from "path";
import * as fs from "fs";
import * as os from "os";
import { spawn, execSync, ChildProcess } from "child_process";
import * as vscode from "vscode";

/**
 * Probe candidate paths in order and return the first one that exists on disk.
 * When no static candidate matches, falls back to a one-time login-shell lookup
 * (`bash -lc 'command -v manul'` / `where manul`) so that conda, pyenv, and
 * other shell-initialised environments are covered. The shell result is cached
 * for the lifetime of the extension host so the blocking call runs at most once.
 */

// Cached result of the shell lookup so we block the extension host at most once.
let _shellResolvedManul: string | undefined;

export function findManulExecutable(workspaceRoot: string): string {
  const custom = vscode.workspace
    .getConfiguration("manulEngine")
    .get<string>("manulPath", "")
    .trim();
  if (custom) {
    return custom;
  }

  const isWin = process.platform === "win32";

  // Ordered list of static candidate paths to probe (no blocking I/O overhead).
  const candidates: string[] = [
    // 1. Project-local venv (highest priority)
    isWin
      ? path.join(workspaceRoot, ".venv", "Scripts", "manul.exe")
      : path.join(workspaceRoot, ".venv", "bin", "manul"),
    // 2. pip --user install (Linux / macOS Intel)
    path.join(os.homedir(), ".local", "bin", "manul"),
    // 3. pipx-managed venv for manul-engine (user-level)
    path.join(os.homedir(), ".local", "pipx", "venvs", "manul-engine", "bin", "manul"),
    // 4. macOS Homebrew — Apple Silicon default prefix
    "/opt/homebrew/bin/manul",
    // 5. system-wide installs
    "/usr/local/bin/manul",
    "/usr/bin/manul",
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  // One-time login-shell lookup — sources ~/.bashrc / conda init / pyenv etc.
  // Result is cached so the blocking call happens at most once per session.
  if (_shellResolvedManul !== undefined) {
    return _shellResolvedManul;
  }
  try {
    const cmd = isWin
      ? "where manul"
      : "bash -lc 'command -v manul'";
    const result = execSync(cmd, { encoding: "utf-8", timeout: 3000 })
      .trim().split("\n")[0].trim();
    if (result && fs.existsSync(result)) {
      _shellResolvedManul = result;
      return result;
    }
  } catch {
    // Shell lookup failed — fall through to bare name.
  }
  _shellResolvedManul = "manul"; // cache the fallback too
  return "manul";
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
