import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import { findManulExecutable, runHunt } from "./huntRunner";

// ── Hunt file step parsing ─────────────────────────────────────────────────

interface HuntStep {
  num: number;
  label: string;
}

function parseHuntSteps(filePath: string): HuntStep[] {
  let content: string;
  try {
    content = fs.readFileSync(filePath, "utf-8");
  } catch {
    return [];
  }
  const steps: HuntStep[] = [];
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith("@")) {
      continue;
    }
    const m = trimmed.match(/^(\d+)\.\s+(.+)/);
    if (m) {
      steps.push({ num: parseInt(m[1], 10), label: m[2].trim() });
    }
  }
  return steps;
}

export function createHuntTestController(
  context: vscode.ExtensionContext
): vscode.TestController {
  const ctrl = vscode.tests.createTestController(
    "manulHuntTests",
    "ManulEngine Hunt Tests"
  );
  context.subscriptions.push(ctrl);

  // ── Discovery ──────────────────────────────────────────────────────────────

  async function discoverHuntFiles(): Promise<void> {
    const files = await vscode.workspace.findFiles("**/*.hunt", "**/{node_modules,.venv,dist}/**");
    for (const uri of files) {
      getOrCreateTestItem(uri);
    }
  }

  function getOrCreateTestItem(uri: vscode.Uri): vscode.TestItem {
    const existing = ctrl.items.get(uri.toString());
    if (existing) {
      return existing;
    }
    const label = path.basename(uri.fsPath, ".hunt");
    const item = ctrl.createTestItem(uri.toString(), label, uri);
    // Steps are added only during a run (for step-level reporting), not at
    // discovery time — otherwise VS Code counts each step as a separate test
    // and the total shown in the explorer is wrong.
    item.canResolveChildren = false;

    ctrl.items.add(item);
    return item;
  }

  function refreshStepChildren(item: vscode.TestItem, uri: vscode.Uri, runId?: number): void {
    item.children.replace([]);
    const steps = parseHuntSteps(uri.fsPath);
    const suffix = runId !== undefined ? `@${runId}` : "";
    for (const step of steps) {
      const stepId = `${uri.toString()}#${step.num}${suffix}`;
      const stepItem = ctrl.createTestItem(stepId, `${step.num}. ${step.label}`, uri);
      stepItem.canResolveChildren = false;
      item.children.add(stepItem);
    }
  }

  // ── File watcher ───────────────────────────────────────────────────────────

  let runCounter = 0;

  const watcher = vscode.workspace.createFileSystemWatcher("**/*.hunt");
  context.subscriptions.push(watcher);

  watcher.onDidCreate((uri) => getOrCreateTestItem(uri));
  watcher.onDidChange((uri) => {
    const existing = ctrl.items.get(uri.toString());
    if (existing) {
      // Clear any leftover step children from a previous run so the count
      // stays at file-level until the next run.
      existing.children.replace([]);
    } else {
      getOrCreateTestItem(uri);
    }
  });
  watcher.onDidDelete((uri) => ctrl.items.delete(uri.toString()));

  discoverHuntFiles();

  // ── Run profile ────────────────────────────────────────────────────────────

  ctrl.createRunProfile(
    "Run Hunt",
    vscode.TestRunProfileKind.Run,
    async (request, token) => {
      const run = ctrl.createTestRun(request);

      // Collect top-level hunt-file items to run (deduplicated)
      const toRun = new Set<vscode.TestItem>();
      function collect(item: vscode.TestItem): void {
        // If it's a child step item, run its parent file instead
        const parentId = item.id.includes("#") ? item.id.split("#")[0] : null;
        if (parentId) {
          const parent = ctrl.items.get(parentId);
          if (parent) {
            toRun.add(parent);
            return;
          }
        }
        toRun.add(item);
      }

      if (request.include) {
        for (const item of request.include) {
          collect(item);
        }
      } else {
        ctrl.items.forEach((item) => toRun.add(item));
      }

      for (const item of toRun) {
        if (token.isCancellationRequested) {
          run.skipped(item);
          continue;
        }

        // Resolve the workspace folder from this specific item's URI so that
        // multi-root workspaces use the correct .venv / config for each file.
        const itemWorkspaceRoot =
          (item.uri ? vscode.workspace.getWorkspaceFolder(item.uri)?.uri.fsPath : undefined)
          ?? vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
          ?? process.cwd();
        const manulExe = await findManulExecutable(itemWorkspaceRoot);

        // Recreate children fresh every run to avoid VS Code's stale state cache
        if (item.uri) {
          refreshStepChildren(item, item.uri, ++runCounter);
        }

        // Build a map of step number → TestItem from children
        const stepItems = new Map<number, vscode.TestItem>();
        item.children.forEach((child) => {
          const m = child.id.match(/#(\d+)(?:@\d+)?$/);
          if (m) {
            stepItems.set(parseInt(m[1], 10), child);
          }
        });

        // Mark all as started
        run.started(item);
        stepItems.forEach((s) => run.started(s));

        const output: string[] = [];

        // Step tracking state
        let currentStepNum = 0;
        let currentStepOutput: string[] = [];
        // Regex to detect step-start lines from the engine
        const stepStartRe = /\[🐾 STEP (\d+) @/;

        function finaliseStep(stepNum: number, failed: boolean): void {
          const stepItem = stepItems.get(stepNum);
          if (!stepItem) { return; }
          const msg = currentStepOutput.join("");
          if (failed) {
            run.failed(stepItem, new vscode.TestMessage(msg));
          } else {
            run.passed(stepItem);
          }
        }

        try {
          const exitCode = await runHunt(
            manulExe,
            item.uri!.fsPath,
            (chunk) => {
              output.push(chunk);
              run.appendOutput(chunk.replace(/\r?\n/g, "\r\n"), undefined, item);

              // Process chunk line-by-line for step tracking.
              // If a new step header appears, the previous step MUST have passed
              // (the engine breaks immediately on any step failure).
              const lines = chunk.split("\n");
              for (const line of lines) {
                const stepMatch = line.match(stepStartRe);
                if (stepMatch) {
                  if (currentStepNum > 0) {
                    finaliseStep(currentStepNum, false); // previous step completed → passed
                  }
                  currentStepNum = parseInt(stepMatch[1], 10);
                  currentStepOutput = [line + "\n"];
                } else {
                  currentStepOutput.push(line + "\n");
                }
              }
            },
            token
          );

          // Finalise the last active step using the exit code as ground truth
          if (currentStepNum > 0) {
            finaliseStep(currentStepNum, exitCode !== 0);
          }

          // Any steps that never started (engine stopped early) → skipped
          stepItems.forEach((s, num) => {
            if (num > currentStepNum) {
              run.skipped(s);
            }
          });

          if (exitCode === 0) {
            run.passed(item);
          } else {
            const fullOutput = output.join("");
            run.failed(item, new vscode.TestMessage(`Exit code: ${exitCode}\n${fullOutput}`));
          }
        } catch (err: unknown) {
          const errMsg = err instanceof Error ? err.message : String(err);
          run.errored(item, new vscode.TestMessage(errMsg));
          // Mark the active step as errored too
          if (currentStepNum > 0) {
            const si = stepItems.get(currentStepNum);
            if (si) { run.errored(si, new vscode.TestMessage(errMsg)); }
          }
        }
      }

      run.end();

      // Remove step children so the explorer reverts to file-level items
      // (correct test count) until the next run.
      toRun.forEach((item) => item.children.replace([]));
    },
    true
  );

  return ctrl;
}

/** Run a single hunt file from context menu / editor title. */
export async function runHuntFileCommand(uri?: vscode.Uri): Promise<void> {
  const target =
    uri ?? vscode.window.activeTextEditor?.document.uri;
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

  const channel = vscode.window.createOutputChannel("ManulEngine");
  channel.show(true);
  channel.appendLine(`🐾 Running: ${path.basename(target.fsPath)}`);
  channel.appendLine(`   manul ${target.fsPath}\n`);

  runHunt(manulExe, target.fsPath, (chunk) => channel.append(chunk)).then(
    (code) => {
      channel.appendLine(
        code === 0 ? "\n✅ PASSED" : `\n❌ FAILED (exit ${code})`
      );
    },
    (err: unknown) => {
      const msg = err instanceof Error ? err.message : String(err);
      channel.appendLine(`\n💥 ERROR: ${msg}`);
    }
  );
}

/** Run hunt file in integrated terminal (raw, like the CLI). */
export async function runHuntFileInTerminalCommand(uri?: vscode.Uri): Promise<void> {
  const target =
    uri ?? vscode.window.activeTextEditor?.document.uri;
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
  const terminal = vscode.window.createTerminal("ManulEngine");
  terminal.show();
  // PowerShell requires `&` to invoke a path-quoted executable; other shells
  // (bash, zsh, fish, cmd) use plain quoting.
  const shellBase = path.basename((vscode.env.shell || "").toLowerCase());
  const isPowerShell = shellBase === "powershell.exe" || shellBase === "pwsh" || shellBase === "pwsh.exe";
  const command = isPowerShell
    ? `& "${manulExe}" "${target.fsPath}"`
    : `"${manulExe}" "${target.fsPath}"`;
  terminal.sendText(command);
}
