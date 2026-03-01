import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";

// ── Tree Item ─────────────────────────────────────────────────────────────────

export class CacheItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly dirPath: string,
    public readonly kind: "root" | "site" | "page",
    collapsible: vscode.TreeItemCollapsibleState
  ) {
    super(label, collapsible);
    this.contextValue = kind === "site" ? "cacheEntry" : kind;
    this.tooltip = dirPath;

    if (kind === "site") {
      this.iconPath = new vscode.ThemeIcon("globe");
      this.description = this._sizeLabel();
    } else if (kind === "page") {
      this.iconPath = new vscode.ThemeIcon("file");
      this.description = this._sizeLabel();
    } else {
      this.iconPath = new vscode.ThemeIcon("database");
    }
  }

  private _sizeLabel(): string {
    try {
      const files = walkFiles(this.dirPath);
      return `${files.length} file${files.length !== 1 ? "s" : ""}`;
    } catch {
      return "";
    }
  }
}

// ── Provider ──────────────────────────────────────────────────────────────────

export class CacheTreeProvider
  implements vscode.TreeDataProvider<CacheItem>
{
  private _onDidChangeTreeData =
    new vscode.EventEmitter<CacheItem | undefined | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private readonly _workspaceRoot: string;

  constructor() {
    const folders = vscode.workspace.workspaceFolders;
    this._workspaceRoot = folders?.[0]?.uri.fsPath ?? process.cwd();
  }

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: CacheItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: CacheItem): vscode.ProviderResult<CacheItem[]> {
    if (!element) {
      return this._getRoots();
    }
    return this._getChildren(element);
  }

  private _cacheDir(): string {
    // Read cache dir from config file
    const configPath = path.join(
      this._workspaceRoot,
      "manul_engine_configuration.json"
    );
    let cacheDir = "cache";
    try {
      const cfg = JSON.parse(
        fs.readFileSync(configPath, "utf-8")
      ) as Record<string, unknown>;
      if (typeof cfg.controls_cache_dir === "string") {
        cacheDir = cfg.controls_cache_dir;
      }
    } catch {
      // use default
    }

    return path.isAbsolute(cacheDir)
      ? cacheDir
      : path.join(this._workspaceRoot, cacheDir);
  }

  private _getRoots(): CacheItem[] {
    const cacheDir = this._cacheDir();
    if (!fs.existsSync(cacheDir)) {
      return [
        new CacheItem(
          "No cache directory found",
          cacheDir,
          "root",
          vscode.TreeItemCollapsibleState.None
        ),
      ];
    }

    const sites = fs
      .readdirSync(cacheDir, { withFileTypes: true })
      .filter((d) => d.isDirectory() && !d.name.startsWith("run_"))
      .map((d) => d.name)
      .sort();

    if (sites.length === 0) {
      return [
        new CacheItem(
          "Cache is empty",
          cacheDir,
          "root",
          vscode.TreeItemCollapsibleState.None
        ),
      ];
    }

    return sites.map(
      (name) =>
        new CacheItem(
          name,
          path.join(cacheDir, name),
          "site",
          vscode.TreeItemCollapsibleState.Collapsed
        )
    );
  }

  private _getChildren(element: CacheItem): CacheItem[] {
    if (!fs.existsSync(element.dirPath)) {
      return [];
    }

    const entries = fs
      .readdirSync(element.dirPath, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => d.name)
      .sort();

    return entries.map(
      (name) =>
        new CacheItem(
          name,
          path.join(element.dirPath, name),
          "page",
          vscode.TreeItemCollapsibleState.None
        )
    );
  }
}

// ── Commands ──────────────────────────────────────────────────────────────────

export async function clearSiteCacheCommand(
  item: CacheItem,
  provider: CacheTreeProvider
): Promise<void> {
  const choice = await vscode.window.showWarningMessage(
    `Delete cache for "${item.label}"? This cannot be undone.`,
    { modal: true },
    "Delete"
  );
  if (choice !== "Delete") {
    return;
  }
  try {
    fs.rmSync(item.dirPath, { recursive: true, force: true });
    provider.refresh();
    vscode.window.showInformationMessage(
      `ManulEngine: cache for "${item.label}" cleared.`
    );
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    vscode.window.showErrorMessage(`Failed to clear cache: ${msg}`);
  }
}

export async function clearAllCacheCommand(
  provider: CacheTreeProvider
): Promise<void> {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    vscode.window.showWarningMessage("No workspace folder open.");
    return;
  }

  const configPath = path.join(
    folders[0].uri.fsPath,
    "manul_engine_configuration.json"
  );
  let cacheDir = path.join(folders[0].uri.fsPath, "cache");
  try {
    const cfg = JSON.parse(
      fs.readFileSync(configPath, "utf-8")
    ) as Record<string, unknown>;
    if (typeof cfg.controls_cache_dir === "string") {
      const d = cfg.controls_cache_dir;
      cacheDir = path.isAbsolute(d)
        ? d
        : path.join(folders[0].uri.fsPath, d);
    }
  } catch {
    // use default
  }

  if (!fs.existsSync(cacheDir)) {
    vscode.window.showInformationMessage("ManulEngine: cache directory does not exist.");
    return;
  }

  const choice = await vscode.window.showWarningMessage(
    `Delete ALL cache in "${path.basename(cacheDir)}"? This cannot be undone.`,
    { modal: true },
    "Delete All"
  );
  if (choice !== "Delete All") {
    return;
  }

  try {
    fs.rmSync(cacheDir, { recursive: true, force: true });
    provider.refresh();
    vscode.window.showInformationMessage(
      "ManulEngine: cache cleared completely."
    );
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    vscode.window.showErrorMessage(`Failed to clear cache: ${msg}`);
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function walkFiles(dir: string): string[] {
  const results: string[] = [];
  try {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        results.push(...walkFiles(full));
      } else {
        results.push(full);
      }
    }
  } catch {
    // skip
  }
  return results;
}
