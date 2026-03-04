import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import {
  createHuntTestController,
  runHuntFileViaController,
  runHuntFileInTerminalCommand,
} from "./huntTestController";
import { ConfigPanelProvider, generateConfigCommand } from "./configPanel";
import {
  CacheTreeProvider,
  CacheItem,
  clearAllCacheCommand,
  clearSiteCacheCommand,
} from "./cacheTreeProvider";

export function activate(context: vscode.ExtensionContext): void {
  // ── Test Controller (Test Explorer) ────────────────────────────────────────
  const ctrl = createHuntTestController(context);

  // ── Config Webview Panel ───────────────────────────────────────────────────
  const configProvider = new ConfigPanelProvider(context);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      ConfigPanelProvider.viewId,
      configProvider
    )
  );

  // ── Cache Tree View ────────────────────────────────────────────────────────
  const cacheProvider = new CacheTreeProvider();
  const cacheView = vscode.window.createTreeView("manul.cacheView", {
    treeDataProvider: cacheProvider,
    showCollapseAll: true,
  });
  context.subscriptions.push(cacheView);

  // ── Commands ───────────────────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("manul.runHuntFile", async (uri?: vscode.Uri) => {
      const target = uri ?? vscode.window.activeTextEditor?.document.uri;
      if (!target || !target.fsPath.endsWith(".hunt")) {
        vscode.window.showWarningMessage("Please open or select a .hunt file.");
        return;
      }
      return runHuntFileViaController(ctrl, target);
    }),

    vscode.commands.registerCommand(
      "manul.runHuntFileInTerminal",
      (uri?: vscode.Uri) => runHuntFileInTerminalCommand(uri)
    ),

    vscode.commands.registerCommand("manul.generateConfig", () =>
      generateConfigCommand()
    ),

    vscode.commands.registerCommand("manul.addDefaultPrompts", () => {
      const folders = vscode.workspace.workspaceFolders;
      if (!folders || folders.length === 0) {
        vscode.window.showWarningMessage("No workspace folder open.");
        return;
      }
      const workspaceRoot = folders[0].uri.fsPath;
      const destDir = path.join(workspaceRoot, "prompts");
      if (fs.existsSync(destDir)) {
        vscode.window.showWarningMessage(
          "ManulEngine: prompts/ folder already exists in workspace."
        );
        return;
      }
      const srcDir = path.join(context.extensionPath, "prompts");
      if (!fs.existsSync(srcDir)) {
        vscode.window.showErrorMessage(
          "ManulEngine: bundled prompts/ folder is missing from the extension package."
        );
        return;
      }
      try {
        fs.mkdirSync(destDir, { recursive: true });
        for (const file of fs.readdirSync(srcDir)) {
          fs.copyFileSync(path.join(srcDir, file), path.join(destDir, file));
        }
        vscode.window.showInformationMessage(
          "ManulEngine: default prompts added to prompts/ folder."
        );
      } catch (err) {
        console.error("ManulEngine: failed to add default prompts.", err);
        vscode.window.showErrorMessage(
          "ManulEngine: failed to add default prompts. Check workspace permissions and try again."
        );
      }
    }),

    vscode.commands.registerCommand("manul.refreshCache", () =>
      cacheProvider.refresh()
    ),

    vscode.commands.registerCommand(
      "manul.clearAllCache",
      () => clearAllCacheCommand(cacheProvider)
    ),

    vscode.commands.registerCommand(
      "manul.clearSiteCache",
      (item: CacheItem) => clearSiteCacheCommand(item, cacheProvider)
    )
  );

  // Refresh cache view when workspace folders change
  context.subscriptions.push(
    vscode.workspace.onDidChangeWorkspaceFolders(() => cacheProvider.refresh())
  );

  // Refresh config view when the config file changes
  const configWatcher = vscode.workspace.createFileSystemWatcher(
    "**/manul_engine_configuration.json"
  );
  context.subscriptions.push(configWatcher);
  configWatcher.onDidChange(() => cacheProvider.refresh());
}

export function deactivate(): void {
  // nothing to clean up (subscriptions handle it)
}
