import * as path from "path";
import * as fs from "fs";
import * as os from "os";
import { exec, spawn, ChildProcess } from "child_process";
import * as vscode from "vscode";

/**
 * Probe candidate paths in order, then falls back to a one-time async
 * login-shell lookup using the user's default shell (`$SHELL -lic 'command -v
 * manul'`), so fish/zsh/bash init scripts and tools like conda, pyenv, and asdf
 * that inject shims via shell hooks are correctly resolved.
 *
 * The shell result is cached per workspaceRoot so the async lookup runs at
 * most once per workspace per extension-host session.
 */

// Per-workspace cache: avoids repeated shell lookups within a session.
const _shellCache = new Map<string, string>();

export async function findManulExecutable(workspaceRoot: string): Promise<string> {
  const custom = vscode.workspace
    .getConfiguration("manulEngine")
    .get<string>("manulPath", "")
    .trim();
  if (custom) {
    return custom;
  }

  const isWin = process.platform === "win32";

  // Ordered list of static candidate paths to probe (synchronous, no overhead).
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

  // Return cached shell result if we already ran the lookup for this workspace.
  if (_shellCache.has(workspaceRoot)) {
    return _shellCache.get(workspaceRoot)!;
  }

  // Async login-shell lookup — sources the user's real shell init so that
  // conda/pyenv/asdf/direnv shims are visible. Uses $SHELL with -lic flags
  // (login + interactive) so both profile and rc files are sourced.
  // cwd is set to workspaceRoot so directory-sensitive tools (direnv, asdf)
  // resolve against the project, consistent with the venv-first search above.
  const result = await new Promise<string>((resolve) => {
    if (isWin) {
      exec("where manul", { cwd: workspaceRoot, timeout: 3000 }, (err, stdout) => {
        const line = stdout.trim().split("\n")[0].trim();
        resolve(!err && line && fs.existsSync(line) ? line : "manul");
      });
    } else {
      const shell = process.env.SHELL || "/bin/sh";
      exec(`${shell} -lic 'command -v manul'`, { cwd: workspaceRoot, timeout: 3000 }, (err, stdout) => {
        const line = stdout.trim().split("\n")[0].trim();
        resolve(!err && line && fs.existsSync(line) ? line : "manul");
      });
    }
  });

  _shellCache.set(workspaceRoot, result);
  return result;
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
