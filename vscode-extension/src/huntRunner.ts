import * as path from "path";
import * as fs from "fs";
import * as os from "os";
import { execFile, spawn, ChildProcess } from "child_process";
import * as vscode from "vscode";

/**
 * Probe candidate paths in order, then falls back to a one-time async
 * login-shell lookup using the user's configured shell (`vscode.env.shell` →
 * `$SHELL`), so fish/zsh/bash init scripts and tools like conda, pyenv, and
 * asdf that inject shims via shell hooks are correctly resolved.
 *
 * The shell result is cached per workspaceRoot so the async lookup runs at
 * most once per workspace per extension-host session.
 */

// Per-workspace cache of in-flight/resolved promises — concurrent calls for the
// same workspaceRoot share one lookup rather than each spawning a shell.
const _shellCache = new Map<string, Promise<string>>();

export async function findManulExecutable(workspaceRoot: string): Promise<string> {
  const custom = vscode.workspace
    .getConfiguration("manulEngine")
    .get<string>("manulPath", "")
    .trim();
  if (custom) {
    if (fs.existsSync(custom)) {
      return custom;
    }
    // Path is configured but doesn't exist — warn and fall through to auto-detection.
    vscode.window.showWarningMessage(
      `ManulEngine: configured manulPath "${custom}" not found. Falling back to auto-detection.`
    );
  }

  const isWin = process.platform === "win32";

  // Ordered list of static candidate paths to probe (synchronous, no overhead).
  // Unix-only paths are excluded on Windows to avoid spurious existsSync probes.
  const candidates: string[] = [
    // 1. Project-local venv — check common folder names (.venv, venv, env, .env)
    ...(['.venv', 'venv', 'env', '.env'].map((dir) =>
      isWin
        ? path.join(workspaceRoot, dir, 'Scripts', 'manul.exe')
        : path.join(workspaceRoot, dir, 'bin', 'manul')
    )),
    // 2+. Platform-specific user-level install locations
    ...(!isWin ? [
      // 2. pip --user install — Linux and macOS Intel common path
      path.join(os.homedir(), ".local", "bin", "manul"),
      // 3. macOS only: pip --user may install to ~/Library/Python/<ver>/bin.
      // Guard with platform and existsSync to avoid a thrown exception on Linux.
      ...(() => {
        if (process.platform !== "darwin") { return []; }
        const base = path.join(os.homedir(), "Library", "Python");
        if (!fs.existsSync(base)) { return []; }
        try {
          return fs.readdirSync(base)
            .map((v) => path.join(base, v, "bin", "manul"))
            .filter((p) => fs.existsSync(p));
        } catch { return []; }
      })(),
      // 4. pipx-managed venv for manul-engine (user-level)
      path.join(os.homedir(), ".local", "pipx", "venvs", "manul-engine", "bin", "manul"),
      // 5. macOS Homebrew — Apple Silicon default prefix
      "/opt/homebrew/bin/manul",
      // 6. system-wide installs
      "/usr/local/bin/manul",
      "/usr/bin/manul",
    ] : [
      // Windows: pip --user installs scripts under %APPDATA%\Python\<ver>\Scripts
      // and %LOCALAPPDATA%\Programs\Python\<ver>\Scripts. Scan both trees.
      ...(() => {
        const results: string[] = [];
        for (const base of [
          process.env.APPDATA ? path.join(process.env.APPDATA, "Python") : "",
          process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, "Programs", "Python") : "",
        ]) {
          if (!base || !fs.existsSync(base)) { continue; }
          try {
            for (const entry of fs.readdirSync(base)) {
              const candidate = path.join(base, entry, "Scripts", "manul.exe");
              if (fs.existsSync(candidate)) { results.push(candidate); }
            }
          } catch { /* ignore */ }
        }
        return results;
      })(),
    ]),
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  // Return the cached promise if a lookup is already in-flight or completed for
  // this workspace — prevents concurrent calls from each spawning a shell.
  if (_shellCache.has(workspaceRoot)) {
    return _shellCache.get(workspaceRoot)!;
  }

  // Async login-shell lookup — sources the user's real shell init so that
  // conda/pyenv/asdf/direnv shims are visible. Uses execFile with an explicit
  // argv array so the shell path is never parsed by another shell (no injection
  // risk even if the path contains spaces). cwd is set to workspaceRoot so
  // directory-sensitive tools (direnv, asdf) resolve against the project.
  const promise = new Promise<string>((resolve) => {
    if (isWin) {
      // `where` is a built-in on Windows; no shell wrapping needed.
      execFile("where", ["manul"], { cwd: workspaceRoot, timeout: 3000 }, (err, stdout) => {
        // `where` can return multiple matches; pick the first that actually exists.
        const found = stdout.split("\n").map(l => l.trim()).find(l => l && fs.existsSync(l));
        resolve(!err && found ? found : "manul");
      });
    } else {
      // Prefer vscode.env.shell (the terminal shell the user configured in VS Code),
      // then fall back to $SHELL. If neither is set, skip the lookup entirely.
      const shell = vscode.env.shell || process.env.SHELL;
      if (!shell) {
        resolve("manul");
        return;
      }
      // Normalise shell name: lowercase and strip .exe suffix so comparisons
      // work on Windows paths (e.g. "fish.exe") and mixed-case entries.
      const shellName = path.basename(shell).toLowerCase().replace(/\.exe$/, "");
      let shellArgs: string[];
      if (shellName === "fish") {
        // fish supports -l (login) and -c but not -i; pass as separate args.
        shellArgs = ["-l", "-c", "command -v manul"];
      } else if (shellName === "sh" || shellName === "dash" || shellName === "ash") {
        shellArgs = ["-c", "command -v manul"];
      } else {
        // bash, zsh, ksh, and most other POSIX-compatible shells.
        shellArgs = ["-l", "-i", "-c", "command -v manul"];
      }
      // argv array avoids shell re-parsing of the shell path (no injection risk).
      execFile(shell, shellArgs, { cwd: workspaceRoot, timeout: 3000 }, (err, stdout) => {
        // Login/interactive shells can emit banners or warnings before the path.
        // Scan all lines and pick the first one that resolves to an existing file.
        const found = stdout.split("\n").map(l => l.trim()).find(l => l && fs.existsSync(l));
        resolve(!err && found ? found : "manul");
      });
    }
  });

  // Store the promise immediately so any concurrent callers await the same lookup.
  // If the lookup fell back to the plain "manul" string (shell init failed or timed
  // out), evict the cache so the next call retries rather than permanently locking
  // in the failure for the rest of the extension-host session.
  const cached = promise.then((result) => {
    if (result === "manul") {
      _shellCache.delete(workspaceRoot);
    }
    return result;
  });
  _shellCache.set(workspaceRoot, cached);
  return cached;
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
      // --workers 1 forces sequential mode so each Test Explorer invocation
      // runs directly in-process (no subprocess spawning overhead / recursion).
      proc = spawn(manulExe, ["--workers", "1", huntFile], {
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
