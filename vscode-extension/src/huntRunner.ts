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
  token?: vscode.CancellationToken,
  breakLines?: number[]
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
      const spawnArgs = ["--workers", "1"];
      if (breakLines && breakLines.length > 0) {
        spawnArgs.push("--break-lines", breakLines.join(","));
      }
      spawnArgs.push(huntFile);
      proc = spawn(manulExe, spawnArgs, {
        cwd,
        env: {
          ...process.env,
          // Force Python to flush stdout immediately — without this, output
          // is block-buffered when piped and steps appear only at the end.
          PYTHONUNBUFFERED: "1",
        },
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

/**
 * Run hunt file in the output-panel (piped) with --debug, implementing the
 * ManulEngine pause-protocol over stdout/stdin.
 *
 * When Python writes  \x00MANUL_DEBUG_PAUSE\x00{"step":"…","idx":N}\n
 * `onPause(step, idx)` is called (the VS Code Webview panel or any custom UI).
 * Its return value ("next" | "continue") is written to the process stdin.
 *
 * Gutter breakpoints also emit the marker (no Playwright Inspector).
 * Regular output lines are forwarded to onData as usual.
 * The function has the same extended signature as runHunt + onPause, and is
 * wrapped as HuntRunFn in huntTestController.ts.
 */
export function runHuntFileDebugPanel(
  manulExe: string,
  huntFile: string,
  onData: (chunk: string) => void,
  token?: vscode.CancellationToken,
  breakLines?: number[],
  onPause?: (step: string, idx: number) => Promise<"next" | "continue">
): Promise<number> {
  const PAUSE_MARKER = "\x00MANUL_DEBUG_PAUSE\x00";
  return new Promise((resolve, reject) => {
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(huntFile));
    const cwd = workspaceFolder?.uri.fsPath ?? path.dirname(huntFile);

    // No --debug flag here: we only want to pause at explicit breakpoints
    // (--break-lines).  Adding --debug would pause before every step.
    const spawnArgs = ["--workers", "1"];
    if (breakLines && breakLines.length > 0) {
      spawnArgs.push("--break-lines", breakLines.join(","));
    }
    spawnArgs.push(huntFile);

    let proc: ChildProcess;
    try {
      proc = spawn(manulExe, spawnArgs, {
        cwd,
        stdio: ["pipe", "pipe", "pipe"],
        env: { ...process.env, PYTHONUNBUFFERED: "1" },
      });
    } catch (err) {
      reject(err);
      return;
    }

    // Line-buffer stdout so we can detect pause markers reliably even if data
    // arrives in chunks smaller than a full line.
    let stdoutBuf = "";
    proc.stdout?.on("data", (d: Buffer) => {
      stdoutBuf += d.toString();
      const lines = stdoutBuf.split("\n");
      stdoutBuf = lines.pop() ?? "";
      for (const line of lines) {
        const markerIdx = line.indexOf(PAUSE_MARKER);
        if (markerIdx !== -1) {
          // Parse the JSON payload that follows the pause marker.
          const jsonPart = line.substring(markerIdx + PAUSE_MARKER.length);
          let step = "";
          let idx = 0;
          try {
            const parsed = JSON.parse(jsonPart) as { step?: string; idx?: number };
            step = parsed.step ?? "";
            idx = parsed.idx ?? 0;
          } catch { /* ignore malformed JSON — still respond so Python doesn't hang */ }

          // Show the Webview panel (if onPause provided) or fall back to
          // a notification.  Either way write the response to stdin so the
          // blocked Python readline() unblocks.
          const pausePromise: Thenable<"next" | "continue"> = onPause
            ? onPause(step, idx)
            : (() => {
                const shortStep = step.length > 100 ? step.substring(0, 100) + "…" : step;
                return vscode.window
                  .showInformationMessage(
                    `🐛 Debug — step ${idx}: ${shortStep}`,
                    { modal: false },
                    "⏭ Next Step",
                    "▶ Continue All"
                  )
                  .then((choice) =>
                    choice === "▶ Continue All" ? "continue" : "next"
                  );
              })();
          pausePromise.then((choice: "next" | "continue") => {
            proc.stdin?.write(choice + "\n");
          });
        } else {
          onData(line + "\n");
        }
      }
    });

    proc.stderr?.on("data", (d: Buffer) => onData(d.toString()));
    proc.on("close", (code) => resolve(code ?? 1));
    proc.on("error", reject);

    token?.onCancellationRequested(() => {
      proc.kill();
      resolve(1);
    });
  });
}

/**
 * Run hunt file in interactive terminal with --debug flag.
 * The user can press ENTER to advance each step, or type 'pause' to open
 * the Playwright Inspector. Gutter breakpoints are also honoured via --break-lines.
 */
export async function runHuntFileDebugInTerminal(
  uri: vscode.Uri,
  workspaceRoot: string,
  manulExe: string
): Promise<void> {
  const shellBase = path.basename((vscode.env.shell || "").toLowerCase());
  const isPowerShell = shellBase === "powershell.exe" || shellBase === "pwsh" || shellBase === "pwsh.exe";
  const breakLines = getHuntBreakpointLines(uri.fsPath);
  const breakFlag = breakLines.length > 0 ? ` --break-lines ${breakLines.join(",")}` : "";
  const command = isPowerShell
    ? `& "${manulExe}" --debug${breakFlag} "${uri.fsPath}"`
    : `"${manulExe}" --debug${breakFlag} "${uri.fsPath}"`;
  const terminal = vscode.window.createTerminal({
    name: "ManulEngine Debug",
    cwd: workspaceRoot,
    env: { PYTHONUNBUFFERED: "1" },
  });
  terminal.show();
  terminal.sendText(command);
}

/**
 * Return 1-based file line numbers of all enabled VS Code breakpoints set
 * inside a given hunt file.  These are passed to the manul CLI as
 * `--break-lines 3,7` so the engine pauses (page.pause()) before each
 * matching step.  Breakpoints show as unverified (grey) in the gutter because
 * ManulEngine does not ship a DAP debug adapter — they still stop execution.
 */
export function getHuntBreakpointLines(huntFilePath: string): number[] {
  const fileFsPath = vscode.Uri.file(huntFilePath).fsPath;
  return vscode.debug.breakpoints
    .filter((bp): bp is vscode.SourceBreakpoint => bp instanceof vscode.SourceBreakpoint)
    .filter((bp) => bp.enabled && bp.location.uri.fsPath === fileFsPath)
    .map((bp) => bp.location.range.start.line + 1); // VS Code lines are 0-based
}
