import * as vscode from "vscode";
import * as path from "path";
import { findManulExecutable, runHunt } from "./huntRunner";

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
    item.canResolveChildren = false;

    // Parse steps as children for better visibility
    try {
      const text = require("fs").readFileSync(uri.fsPath, "utf-8") as string;
      const lines: string[] = text.split("\n");
      const stepItems: vscode.TestItem[] = [];
      for (const line of lines) {
        const m = line.match(/^\s*(\d+)\.\s+(.+)/);
        if (m) {
          const stepId = `${uri.toString()}#${m[1]}`;
          const stepItem = ctrl.createTestItem(stepId, `${m[1]}. ${m[2].trim()}`);
          stepItem.canResolveChildren = false;
          stepItems.push(stepItem);
        }
      }
      if (stepItems.length > 0) {
        item.children.replace(stepItems);
      }
    } catch {
      // ignore parse errors
    }

    ctrl.items.add(item);
    return item;
  }

  // ── File watcher ───────────────────────────────────────────────────────────

  const watcher = vscode.workspace.createFileSystemWatcher("**/*.hunt");
  context.subscriptions.push(watcher);

  watcher.onDidCreate((uri) => getOrCreateTestItem(uri));
  watcher.onDidChange((uri) => {
    ctrl.items.delete(uri.toString());
    getOrCreateTestItem(uri);
  });
  watcher.onDidDelete((uri) => ctrl.items.delete(uri.toString()));

  discoverHuntFiles();

  // ── Run profile ────────────────────────────────────────────────────────────

  ctrl.createRunProfile(
    "Run Hunt",
    vscode.TestRunProfileKind.Run,
    async (request, token) => {
      const run = ctrl.createTestRun(request);
      const roots = vscode.workspace.workspaceFolders ?? [];
      const workspaceRoot = roots[0]?.uri.fsPath ?? process.cwd();
      const manulExe = findManulExecutable(workspaceRoot);

      // Collect top-level items to run (deduplicated by hunt file)
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

        run.started(item);
        const output: string[] = [];

        try {
          const exitCode = await runHunt(
            manulExe,
            item.uri!.fsPath,
            (chunk) => {
              output.push(chunk);
              run.appendOutput(chunk.replace(/\r?\n/g, "\r\n"), undefined, item);
            },
            token
          );

          if (exitCode === 0) {
            run.passed(item);
            // Mark child steps as passed too
            item.children.forEach((child) => run.passed(child));
          } else {
            const msg = new vscode.TestMessage(
              `Exit code: ${exitCode}\n${output.join("")}`
            );
            run.failed(item, msg);
          }
        } catch (err: unknown) {
          const errMsg = err instanceof Error ? err.message : String(err);
          run.errored(item, new vscode.TestMessage(errMsg));
        }
      }

      run.end();
    },
    true
  );

  return ctrl;
}

/** Run a single hunt file from context menu / editor title. */
export function runHuntFileCommand(uri?: vscode.Uri): void {
  const target =
    uri ?? vscode.window.activeTextEditor?.document.uri;
  if (!target || !target.fsPath.endsWith(".hunt")) {
    vscode.window.showWarningMessage("Please open or select a .hunt file.");
    return;
  }

  const roots = vscode.workspace.workspaceFolders ?? [];
  const workspaceRoot = roots[0]?.uri.fsPath ?? process.cwd();
  const manulExe = findManulExecutable(workspaceRoot);

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
export function runHuntFileInTerminalCommand(uri?: vscode.Uri): void {
  const target =
    uri ?? vscode.window.activeTextEditor?.document.uri;
  if (!target || !target.fsPath.endsWith(".hunt")) {
    vscode.window.showWarningMessage("Please open or select a .hunt file.");
    return;
  }

  const roots = vscode.workspace.workspaceFolders ?? [];
  const workspaceRoot = roots[0]?.uri.fsPath ?? process.cwd();
  const manulExe = findManulExecutable(workspaceRoot);
  const terminal = vscode.window.createTerminal("ManulEngine");
  terminal.show();
  terminal.sendText(`"${manulExe}" "${target.fsPath}"`);
}
